"""Fail-closed schemas at the evidence and feature boundaries."""
import math
import re

FIELDS = {
    "packet": {"ip_protocol", "source_endpoint", "destination_endpoint", "source_port", "destination_port", "tcp_flags", "packet_length"},
    "message": {"apci_format", "asdu_type", "cause_of_transmission"},
    "process": {"channel_id", "family", "attribute", "context"},
}
FORBIDDEN = {"malicious", "label", "event_truth", "attack_point", "description", "initial_value", "scenario", "recording", "recovery"}
ATTRIBUTES = {
    'voltage': {'voltage','voltage_from','voltage_to','voltage_hv','voltage_lv'},
    'current': {'current_from','current_to','current_hv','current_lv'},
    'active_power': {'active_power','active_power_from','active_power_to','active_power_hv','active_power_lv'},
    'reactive_power': {'reactive_power','reactive_power_from','reactive_power_to','reactive_power_hv','reactive_power_lv'},
    'reported_state': {'is_closed','is_connected'},
}
UNITS = dict(zip(ATTRIBUTES, ['PER_UNIT','AMPERE','WATT','VAR','NONE']))


def validate_channel(channel, m):
    if not re.fullmatch(r'ch_[0-9a-f]{16}', channel):
        raise ValueError('Non-opaque channel')
    if set(m) != {'asset_id','family','attribute','context','unit','scale'}:
        raise ValueError('Unapproved mapping metadata')
    if not re.fullmatch(r'asset_[0-9a-f]{16}',m['asset_id']):
        raise ValueError('Non-opaque mapping asset')
    if m['family'] not in ATTRIBUTES or m['attribute'] not in ATTRIBUTES[m['family']]:
        raise ValueError('Unapproved process attribute')
    if m['unit'] != UNITS[m['family']] or m['scale'] not in ('BASE','NONE') or m['context']!='MEASUREMENT':
        raise ValueError('Unapproved unit/context')


def validate_record(r):
    if r.source_type not in FIELDS or set(r.fields) != FIELDS[r.source_type]:
        raise ValueError("Unapproved evidence fields")
    if not re.fullmatch(r"src_[0-9a-f]{20}",r.source_file):
        raise ValueError("Raw filename leakage")
    if not re.fullmatch(r"[pme]_[0-9a-f]{24}",r.evidence_id):
        raise ValueError("Non-opaque evidence ID")
    if not re.fullmatch(r"vp_[0-9a-f]{16}",r.vantage_point):
        raise ValueError("Raw vantage leakage")
    if r.asset_id is not None and not re.fullmatch(r"asset_[0-9a-f]{16}",r.asset_id):
        raise ValueError("Invalid asset identifier")
    if type(r.observation_time) not in (int,float) or not math.isfinite(r.observation_time):
        raise ValueError("Invalid observation time")
    if r.reported_time is not None:
        raise ValueError("Decoder v1 does not invent reported measurement times")
    if r.transformation != 'pcap-iec104-v1' or r.protocol not in ('TCP','OTHER','IEC104'):
        raise ValueError('Unapproved transformation/protocol')
    if not set(r.quality_flags) <= {'invalid','not_topical','substituted','blocked','overflow','nonfinite'}:
        raise ValueError('Unapproved quality flags')
    if r.value is not None and (type(r.value) not in (int,float,bool) or not math.isfinite(r.value)):
        raise ValueError("Unapproved or nonfinite value")
    if r.source_type == "process":
        if r.view != "E" or r.fields["context"] != "MEASUREMENT":
            raise ValueError("Configuration or network content cannot enter E")
        f = r.fields['family']
        if f not in ATTRIBUTES or r.fields['attribute'] not in ATTRIBUTES[f] or r.unit != UNITS[f]:
            raise ValueError('Unapproved process field/unit')
        if r.value is not None and ((f=='reported_state') != isinstance(r.value,bool)):
            raise ValueError('Boolean/numeric process type mismatch')
    elif r.view != "N" or r.value is not None or r.unit is not None:
        raise ValueError("Process payload cannot enter N")
    if r.source_type == 'packet':
        for key in ('source_endpoint','destination_endpoint'):
            if r.fields[key] is not None and not re.fullmatch(r'ep_[0-9a-f]{16}',r.fields[key]):
                raise ValueError('Raw endpoint leakage')
        for key in ('ip_protocol','source_port','destination_port','tcp_flags','packet_length'):
            v = r.fields[key]
            if v is not None and (type(v) is not int or v<0):
                raise ValueError('Invalid packet header')
    if r.source_type == 'message':
        if r.fields['apci_format'] not in ('I','S','U'):
            raise ValueError('Invalid APCI format')
        for k in ('asdu_type','cause_of_transmission'):
            if r.fields[k] is not None and (type(r.fields[k]) is not int or not 0<=r.fields[k]<=255):
                raise ValueError('Invalid ASDU header')


def validate_features(values, allowlist):
    if set(values) != set(allowlist) or set(values) & FORBIDDEN:
        raise ValueError("Feature allowlist violation / label leakage")
    for name, value in values.items():
        if value is not None and (type(value) not in (int,float) or not math.isfinite(value)):
            raise ValueError(f"Non-numeric or nonfinite feature: {name}")
    return values
