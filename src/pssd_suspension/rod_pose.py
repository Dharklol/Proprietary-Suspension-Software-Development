"""Conditional no-axial-spin offset transport; BENCH-VEH-0027."""
import math


def _dot(a,b): return sum(x*y for x,y in zip(a,b))
def _cross(a,b): return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
def _scale(s,v): return tuple(s*x for x in v)
def _add(*vectors): return tuple(sum(v[i] for v in vectors) for i in range(3))


def transport_rod_offset(u0,u,up,offset):
    """Rotate an offset by shortest rotation u0->u and differentiate it.

u0/u are unit directions, up is du/dq (tangent to u), offset is in m. Returned
derivative has m per coordinate unit. This is an explicit axial-spin gauge,
not a source-derived material frame; antiparallel directions are rejected.
"""
    if any(len(v)!=3 or not all(math.isfinite(x) for x in v) for v in (u0,u,up,offset)):
        raise ValueError('Finite three-vectors required')
    if abs(_dot(u0,u0)-1)>1e-10 or abs(_dot(u,u)-1)>1e-10 or abs(_dot(u,up))>1e-10:
        raise ValueError('Unit directions and tangent direction derivative required')
    c=_dot(u0,u)
    if 1+c<1e-8: raise ValueError('Antiparallel rod pose is not supported')
    v=_cross(u0,u);vp=_cross(u0,up);cp=_dot(u0,up)
    vv=_cross(v,_cross(v,offset))
    rotated=_add(offset,_cross(v,offset),_scale(1/(1+c),vv))
    derivative=_add(_cross(vp,offset),_scale(1/(1+c),_add(_cross(vp,_cross(v,offset)),_cross(v,_cross(vp,offset)))),_scale(-cp/(1+c)**2,vv))
    return rotated,derivative
