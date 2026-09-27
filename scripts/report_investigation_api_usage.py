"""Read retained attempt meters; compute known-usage list-price subtotal only."""
import collections,json,sys
from decimal import Decimal
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from investigation_dryrun.common import load,binding,create_json,utc
OUT=ROOT/'results/investigation-dryrun-v1'
RATES={'default':{'uncached_input':'2.00','cached_input':'0.50','output':'8.00'},'priority':{'uncached_input':'3.50','cached_input':'0.875','output':'14.00'}}
SOURCE='https://developers.openai.com/api/docs/pricing'

def cost(usage,tier):
    cached=(usage.get('input_tokens_details') or {}).get('cached_tokens')
    values=[usage.get('input_tokens'),cached,usage.get('output_tokens')]
    if any(type(x) is not int or x<0 for x in values) or cached>usage['input_tokens']:return None
    if tier not in RATES:return None
    rates=RATES[tier]
    return (Decimal(usage['input_tokens']-cached)*Decimal(rates['uncached_input'])+Decimal(cached)*Decimal(rates['cached_input'])+Decimal(usage['output_tokens'])*Decimal(rates['output']))/Decimal(1_000_000)

def build():
    rows=[];missing=[];response_ids=set();total=collections.Counter();prices=[];byrun=collections.defaultdict(collections.Counter)
    for path in sorted((OUT/'runs').glob('*/*/*/rep-*/attempt-*/attempt.json')):
        a=load(path);m=a.get('provider_metadata') or {};u=m.get('usage');run=path.relative_to(OUT/'runs').parts[0]
        if not u:
            missing.append({'attempt':binding(path),'HTTP_status':a.get('HTTP_status'),'reason':a.get('reason'),'usage':None,'cost':None});continue
        rid=m.get('id')
        if not rid or rid in response_ids:raise ValueError('Missing or duplicate provider response ID; cost reconciliation required')
        response_ids.add(rid)
        cached=(u.get('input_tokens_details') or {}).get('cached_tokens')
        values={'input_tokens':u.get('input_tokens'),'cached_input_tokens':cached,'uncached_input_tokens':u['input_tokens']-cached if type(cached) is int else None,'output_tokens':u.get('output_tokens'),'total_tokens':u.get('total_tokens')}
        if type(values['total_tokens']) is int and values['total_tokens']!=values['input_tokens']+values['output_tokens']:raise ValueError('Provider token total mismatch')
        price=cost(u,m.get('service_tier')) if m.get('model')=='gpt-4.1-2025-04-14' else None
        if price is not None:prices.append(price)
        for k,v in values.items():
            if type(v) is int:total[k]+=v;byrun[run][k]+=v
        rows.append({'attempt':binding(path),'response_id':rid,'model':m.get('model'),'service_tier':m.get('service_tier'),'status':m.get('status'),'tokens':values,'estimated_list_price_USD':str(price) if price is not None else None})
    return {'created_at':utc(),'scope':'All retained original and separately authorized recovery attempts, including incomplete responses; no output selection','pricing_source':SOURCE,'pricing_verified_date':'2026-09-26','rate_unit':'USD per 1,000,000 tokens','rates':RATES,'cost_formula':'(input_tokens - cached_input_tokens)*uncached_input_rate/1e6 + cached_input_tokens*cached_input_rate/1e6 + output_tokens*output_rate/1e6','cached_input_is_subset_of_input_not_additional':True,'known_usage_totals':dict(total),'known_usage_by_run':{k:dict(v) for k,v in byrun.items()},'metered_response_count':len(rows),'priced_response_count':len(prices),'known_usage_list_price_subtotal_USD':str(sum(prices,Decimal(0))),'total_actual_invoice_cost_USD':None,'billing_limitations':'Known-response list-price estimate, not a billing invoice. Missing usage, unknown deliveries, account credits/discounts/tax and other account traffic cannot be reconstructed here; never assume zero cost for missing usage. No model/API billing queries made.','unmetered_attempt_count':len(missing),'unmetered_HTTP_counts':dict(collections.Counter(str(x['HTTP_status']) for x in missing)),'metered_attempts':rows,'unmetered_attempts':missing}

if __name__=='__main__':
 r=build();create_json(OUT/'api_usage_and_cost.json',r)
 lines=['# Development Dry Run — API usage and cost','',f"Known input tokens: {r['known_usage_totals'].get('input_tokens',0):,}",f"Cached input tokens (included in input): {r['known_usage_totals'].get('cached_input_tokens',0):,}",f"Uncached input tokens: {r['known_usage_totals'].get('uncached_input_tokens',0):,}",f"Output tokens: {r['known_usage_totals'].get('output_tokens',0):,}",f"Known total tokens: {r['known_usage_totals'].get('total_tokens',0):,}",'',f"Known-usage list-price subtotal: **USD {r['known_usage_list_price_subtotal_USD']}**.",'',f"Metered responses: {r['metered_response_count']}. Attempts without usage: {r['unmetered_attempt_count']}; unknown delivery cost is not assumed to be zero.",'',f"Source: [OpenAI API pricing]({SOURCE}), checked 2026-09-26. Standard GPT-4.1 per million tokens: uncached input $2.00, cached input $0.50, output $8.00.",'',r['billing_limitations'],'','Original/recovery breakdown and exact attempt hashes: `results/investigation-dryrun-v1/api_usage_and_cost.json`.']
 (ROOT/'docs/investigation_api_usage.r4.md').write_text('\n\n'.join(lines)+'\n')
 print(json.dumps({k:r[k] for k in ['known_usage_totals','known_usage_list_price_subtotal_USD','metered_response_count','unmetered_attempt_count']},indent=2))
