"""How far does each feature stand off ITS OWN panel? That is what relief needs.

AND THE ANSWER IS ONLY AS GOOD AS THE POSE, which this cannot check for you. The
R740XD supply is drawn with its withdrawal handle SWUNG OPEN, because the guide
is a removal procedure - so every protrusion measured off it is measuring an open
handle, and the giveaway is that the unit boxes 132.6 wide against an 86.3 body.
A part whose envelope is much larger than its body is posed, not shaped.

NOT how far it is from the origin, and not how far from the chassis - how far
from the face it is mounted on. Within one rigid part that is reliable even in an
exploded pose, because a withdrawn supply carries its own latch and screws
withdrawn with it. Across parts a guide may have moved independently it is not,
and this says which is which by only ever comparing inside a subtree.

Positive is PROUD of the face; negative is recessed behind it.
"""
import json
import pathlib
import struct
import sys

b = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else
                 'working/intake/dell/3d-models/r740xd.glb').read_bytes()
off, js = 12, None
while off < len(b):
    ln, kind = struct.unpack_from('<II', b, off)
    if kind == 0x4E4F534A:
        js = json.loads(b[off + 8:off + 8 + ln])
    off += 8 + ln
nodes = js['nodes']
parent = {}
for i, n in enumerate(nodes):
    for c in n.get('children', []):
        parent[c] = i


def mul(a, c):
    return [sum(a[i + k * 4] * c[k + j * 4] for k in range(4))
            for j in range(4) for i in range(4)]


def local(n):
    if 'matrix' in n:
        return list(n['matrix'])
    t = n.get('translation', [0, 0, 0])
    x, y, z, w = n.get('rotation', [0, 0, 0, 1])
    s = n.get('scale', [1, 1, 1])
    return [(1 - 2 * (y * y + z * z)) * s[0], (2 * (x * y + z * w)) * s[0],
            (2 * (x * z - y * w)) * s[0], 0,
            (2 * (x * y - z * w)) * s[1], (1 - 2 * (x * x + z * z)) * s[1],
            (2 * (y * z + x * w)) * s[1], 0,
            (2 * (x * z + y * w)) * s[2], (2 * (y * z - x * w)) * s[2],
            (1 - 2 * (x * x + y * y)) * s[2], 0, t[0], t[1], t[2], 1]


def ap(m, p):
    return (m[0] * p[0] + m[4] * p[1] + m[8] * p[2] + m[12],
            m[1] * p[0] + m[5] * p[1] + m[9] * p[2] + m[13],
            m[2] * p[0] + m[6] * p[1] + m[10] * p[2] + m[14])


def world(i):
    ch = []
    j = i
    while j in parent:
        j = parent[j]
        ch.append(j)
    m = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    for j in reversed(ch):
        m = mul(m, local(nodes[j]))
    return m


def box(i, m=None, acc=None):
    if acc is None:
        acc = [[1e30] * 3, [-1e30] * 3]
        m = world(i)
    n = nodes[i]
    m = mul(m, local(n))
    if 'mesh' in n:
        for prim in js['meshes'][n['mesh']].get('primitives', []):
            pos = prim.get('attributes', {}).get('POSITION')
            if pos is None:
                continue
            a = js['accessors'][pos]
            if 'min' not in a:
                continue
            for cx in range(8):
                q = ap(m, [a['max' if cx >> k & 1 else 'min'][k]
                           for k in range(3)])
                for k in range(3):
                    acc[0][k] = min(acc[0][k], q[k])
                    acc[1][k] = max(acc[1][k], q[k])
    for c in n.get('children', []):
        box(c, m, acc)
    return acc if acc[1][0] > -1e29 else None


root = sys.argv[1].lower()
top = [i for i, n in enumerate(nodes) if root in n.get('name', '').lower()]
if not top:
    raise SystemExit('no such part')
i = top[0]
rb = box(i)
face = rb[1][2] * 1000
print(f'{nodes[i]["name"]}')
print(f'  its own front face is at z {face:.1f}; everything below is measured '
      f'FROM THAT\n')

seen = set()
rows = []


def descend(k):
    n = nodes[k]
    nm = n.get('name', '')
    if nm and k != i:
        bb = box(k)
        if bb:
            z1 = bb[1][2] * 1000
            z0 = bb[0][2] * 1000
            key = (nm, round(z1, 1), round(z0, 1))
            if key not in seen:
                seen.add(key)
                rows.append((nm, z1 - face, z1 - z0,
                             (bb[1][0] - bb[0][0]) * 1000,
                             (bb[1][1] - bb[0][1]) * 1000))
    for c in n.get('children', []):
        descend(c)


descend(i)
print(f'{"feature":<44} {"proud":>8} {"deep":>8} {"w":>7} {"h":>7}')
print('-' * 78)
for nm, proud, deep, w, h in sorted(rows, key=lambda r: -r[1]):
    note = '' if proud > 0.05 else ('  flush' if proud > -0.5 else '  RECESSED')
    print(f'{nm[:44]:<44} {proud:8.2f} {deep:8.1f} {w:7.1f} {h:7.1f}{note}')
print('\nproud > 0 stands off the face; < 0 sits behind it. Depths are the '
      'part\'s own\nextent along z, which is not the same question.')
