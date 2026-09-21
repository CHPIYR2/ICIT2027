import numpy as np
from sklearn.metrics import (average_precision_score, balanced_accuracy_score, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score)


def classification_metrics(y, scores, threshold=.5):
    y=np.asarray(y);scores=np.asarray(scores);pred=(scores>=threshold).astype(int)
    tn,fp,fn,tp=map(int,confusion_matrix(y,pred,labels=[0,1]).ravel())
    both=len(set(y.tolist()))==2
    return {'n':len(y),'benign':tn+fp,'cyber':tp+fn,'confusion_matrix_order':['BENIGN','CYBER'],
            'confusion_matrix':[[tn,fp],[fn,tp]],
            'precision_cyber':float(precision_score(y,pred,zero_division=0)),
            'recall_cyber':float(recall_score(y,pred,zero_division=0)) if tp+fn else None,
            'f1_cyber':float(f1_score(y,pred,zero_division=0)) if tp+fn else None,
            'macro_f1':float(f1_score(y,pred,labels=[0,1],average='macro',zero_division=0)) if both else None,
            'balanced_accuracy':float(balanced_accuracy_score(y,pred)) if both else None,
            'auroc':float(roc_auc_score(y,scores)) if both else None,
            'auprc':float(average_precision_score(y,scores)) if both else None,
            'false_cyber_attribution':{'numerator':fp,'denominator':tn+fp,'rate':fp/(tn+fp) if tn+fp else None},
            'missed_cyber':{'numerator':fn,'denominator':fn+tp,'rate':fn/(fn+tp) if fn+tp else None}}
