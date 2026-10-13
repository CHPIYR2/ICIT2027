import gzip
import io
import json
from mirage_ot.stream import iter_json_records
from mirage_ot.ipal import iter_state, unix_seconds


def test_stream_array_cross_chunk():
    rows = [{'timestamp': i, 'values': {'bus.0.MEASUREMENT.voltage': i / 10}} for i in range(7)]
    s = io.StringIO(json.dumps(rows))
    assert list(iter_json_records(s)) == rows


def test_stream_ndjson():
    s = io.StringIO('{"a":1}\n{"b":2}\n')
    assert list(iter_json_records(s)) == [{'a':1},{'b':2}]


def test_ipal_gzip_meas_and_bool():
    text = json.dumps([{'timestamp': 1700000000, 'values': {'switch.4.MEASUREMENT.is_closed': True,
                'bus.1.MEASUREMENT.voltage': 1.02, 'missing': None}}])
    stream = io.BytesIO(gzip.compress(text.encode()))
    rows = list(iter_state(stream, source='train.n302.state.gz'))
    assert len(rows) == 2
    assert rows[0].value == 1.0
    assert all('network-reported' == x.attrs['trust'] for x in rows)


def test_utc_timestamp():
    assert unix_seconds('2024-01-01T00:00:00Z') == 1704067200
