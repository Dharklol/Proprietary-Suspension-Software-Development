"""Vertical reaction family on symmetric two-axle supports; BENCH-VEH-0025."""
import math


def reaction_family(mass,cg,front_x,rear_x,front_half_track,rear_half_track,g=9.81):
    """All vertical reactions satisfying weight/pitch/roll; one free front-left load."""
    if len(cg)!=3: raise ValueError('Three-component CG required')
    if not all(math.isfinite(v) for v in (mass,*cg,front_x,rear_x,front_half_track,rear_half_track,g)):
        raise ValueError('Finite geometry and mass required')
    if mass<=0 or g<=0 or front_half_track<=0 or rear_half_track<=0 or front_x<=rear_x:
        raise ValueError('Positive mass/gravity/track and ordered axle stations required')
    W=mass*g;front=W*(cg[0]-rear_x)/(front_x-rear_x);rear=W-front
    yf,yr=front_half_track,rear_half_track
    lo=max(0.,(W*cg[1]+yf*front-yr*rear)/(2*yf))
    hi=min(front,(W*cg[1]+yf*front+yr*rear)/(2*yf))
    if lo>hi: raise ValueError('CG outside nonnegative support polygon')
    def loads(lf):
        difference=(W*cg[1]-yf*(2*lf-front))/yr
        return (lf,front-lf,.5*(rear+difference),.5*(rear-difference))
    return dict(weight_N=W,front_axle_N=front,rear_axle_N=rear,front_left_parameter_interval_N=(lo,hi),
                endpoint_loads_N=(loads(lo),loads(hi)),corner_loads_unique=hi-lo<=1e-12)

