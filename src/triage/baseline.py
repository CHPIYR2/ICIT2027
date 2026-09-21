"""Training-only preprocessing and explicit feature allowlists."""
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import MissingIndicator, SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import StandardScaler

from features.extract import E_NAMES, N_NAMES
from sherlock.sanitizer import validate_features


def names(view):
    if view not in ('E','N','EN'): raise ValueError('Unknown view')
    return (E_NAMES if 'E' in view else [])+(N_NAMES if 'N' in view else [])


def matrix(rows, view):
    for row in rows:
        validate_features(row['values'],E_NAMES+N_NAMES)
    return np.asarray([[float('nan') if row['values'][name] is None else row['values'][name]
                        for name in names(view)] for row in rows],dtype=float)


def make_pipeline(model_name, config):
    classes = {'logistic_regression':LogisticRegression,'random_forest':RandomForestClassifier,
               'gradient_boosting':GradientBoostingClassifier}
    estimator = classes[model_name](**config['models'][model_name],random_state=config['seed'])
    return Pipeline([
        ('missing',FeatureUnion([
            ('values',SimpleImputer(strategy='median',keep_empty_features=True)),
            ('indicators',MissingIndicator(features='all'))])),
        ('scaler',StandardScaler()), ('model',estimator)])


def contributions(pipeline, x, feature_names):
    """Exact logistic log-odds accounting, not a causal explanation."""
    if not isinstance(pipeline['model'],LogisticRegression): return None
    z=pipeline[:-1].transform(x)
    contributions=z*pipeline['model'].coef_[0]
    labels=feature_names+[n+'__missing' for n in feature_names]
    return [{'intercept':float(pipeline['model'].intercept_[0]),
             'log_odds_contributions':dict(zip(labels,map(float,row))),
             'interpretation':'Additive model log-odds contributions; not causal effects.'} for row in contributions]
