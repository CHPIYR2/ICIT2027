"""CLEARLY SYNTHETIC smoke-test observations. Never use as paper efficacy data."""
import json
import math
import random
from pathlib import Path
from .types import Observation


def generate(path: Path, *, bins=64, bin_seconds=10.0, seed=7):
    rng = random.Random(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as f:
        def write(t, m, entity, kind, value, attr=None):
            ix = generate.serial
            generate.serial += 1
            obs = Observation(t, m, entity, kind, value, f'synthetic:#row={ix}', attr)
            f.write(json.dumps(obs.to_json(), ensure_ascii=False) + '\n')
        generate.serial = 0
        for i in range(bins):
            time = 1_700_000_000 + i*bin_seconds
            latent = math.sin(i/6)
            for name, base in [('192.0.2.10:2404->192.0.2.20:4000/TCP', 6),
                               ('192.0.2.20:4000->192.0.2.10:2404/TCP', 4),
                               ('192.0.2.30->192.0.2.10/ARP', 3)]:
                n = max(1, int(base + 2*latent + rng.uniform(-1,1)))
                for j in range(n):
                    arp = name.endswith('/ARP')
                    write(time + j*.05, 'network', name, 'arp_packet' if arp else 'tcp_packet',
                          1 if arp else 100+j,
                          {} if arp else {'payload_bytes': j, 'iec104_candidate': 1, 'tcp_flags': 16})
            for channel, offset in [('bus.0.MEASUREMENT.voltage', 1.0),
                                    ('line.1.MEASUREMENT.current_from', 20.0),
                                    ('load.3.MEASUREMENT.active_power', 100.0)]:
                write(time+.7, 'physical', channel, 'observed_telemetry',
                      offset+2*latent+rng.gauss(0,.05),
                      {'trust':'network-reported'})
