"""Local rigid-member kinetic-energy reduction (AUTH-SUSP-0021/EQ-SUSP-0039)."""
from dataclasses import dataclass
import math


def _psd3(a, tolerance=1e-12):
    return (all(a[i][i]>=-tolerance for i in range(3))
        and all(a[i][i]*a[j][j]-a[i][j]*a[j][i]>=-tolerance for i,j in ((0,1),(0,2),(1,2)))
        and (a[0][0]*(a[1][1]*a[2][2]-a[1][2]*a[2][1])
             -a[0][1]*(a[1][0]*a[2][2]-a[1][2]*a[2][0])
             +a[0][2]*(a[1][0]*a[2][1]-a[1][1]*a[2][0]))>=-tolerance)


@dataclass(frozen=True)
class RigidMemberKinematics:
    member_id: str
    source_id: str
    configuration_id: str
    frame_id: str
    state_id: str
    coordinate_ids: tuple[str,...]
    coordinate_units: tuple[str,...]
    mass_kg: float
    centroidal_tensor_kg_m2: tuple[tuple[float,...],...]
    cg_velocity_jacobian: tuple[tuple[float,...],...]
    angular_velocity_jacobian: tuple[tuple[float,...],...]

    def __post_init__(self):
        if not all((self.member_id,self.source_id,self.configuration_id,self.frame_id,self.state_id)):
            raise ValueError('Member and source/configuration/frame/state identities required')
        n=len(self.coordinate_ids)
        if not n or len(set(self.coordinate_ids))!=n or not all(self.coordinate_ids):
            raise ValueError('Nonempty unique coordinate IDs required')
        if len(self.coordinate_units)!=n or not all(self.coordinate_units):
            raise ValueError('Explicit coordinate units required')
        if not math.isfinite(self.mass_kg) or self.mass_kg<=0:
            raise ValueError('Positive finite member mass required')
        for matrix,columns in ((self.centroidal_tensor_kg_m2,3),(self.cg_velocity_jacobian,n),(self.angular_velocity_jacobian,n)):
            if len(matrix)!=3 or any(len(row)!=columns for row in matrix):
                raise ValueError('Tensor/Jacobian shape mismatch')
            if not all(math.isfinite(x) for row in matrix for x in row):
                raise ValueError('Finite tensor/Jacobians required')
        tensor=self.centroidal_tensor_kg_m2
        scale=max(abs(x) for row in tensor for x in row)
        if scale==0: return
        a=tuple(tuple(x/scale for x in row) for row in tensor)
        if any(abs(a[i][j]-a[j][i])>1e-12 for i in range(3) for j in range(3)):
            raise ValueError('Physical tensor must be symmetric')
        if not _psd3(a): raise ValueError('Negative centroidal inertia')
        half_trace=sum(a[i][i] for i in range(3))/2
        second_moment=tuple(tuple((half_trace if i==j else 0.)-a[i][j] for j in range(3)) for i in range(3))
        if not _psd3(second_moment): raise ValueError('Unrealizable mass inertia tensor')


@dataclass(frozen=True)
class ReducedMassMatrix:
    coordinate_ids: tuple[str,...]
    coordinate_units: tuple[str,...]
    configuration_id: str
    frame_id: str
    state_id: str
    members: tuple[RigidMemberKinematics,...]
    matrix: tuple[tuple[float,...],...]

    def kinetic_energy_J(self, coordinate_rates):
        rates=tuple(coordinate_rates)
        if len(rates)!=len(self.coordinate_ids) or not all(math.isfinite(v) for v in rates):
            raise ValueError('Finite rate vector matching coordinate order required')
        energy=.5*sum(rates[i]*self.matrix[i][j]*rates[j] for i in range(len(rates)) for j in range(len(rates)))
        if not math.isfinite(energy): raise ValueError('Nonfinite kinetic energy')
        return energy


def reduce_member_inertia(members, *, expected_member_ids) -> ReducedMassMatrix:
    members=tuple(members)
    expected=tuple(expected_member_ids)
    if not members or len(set(expected))!=len(expected):
        raise ValueError('Nonempty members and unique expected member manifest required')
    actual=tuple(m.member_id for m in members)
    if len(set(actual))!=len(actual) or set(actual)!=set(expected):
        raise ValueError('Duplicate, missing or unexpected member')
    reference=members[0]
    key=lambda m:(m.coordinate_ids,m.coordinate_units,m.configuration_id,m.frame_id,m.state_id)
    if any(key(m)!=key(reference) for m in members):
        raise ValueError('Coordinate/configuration/frame/state mismatch')
    n=len(reference.coordinate_ids)
    matrix=[[0.]*n for _ in range(n)]
    for m in members:
        v,w,I=m.cg_velocity_jacobian,m.angular_velocity_jacobian,m.centroidal_tensor_kg_m2
        for i in range(n):
            for j in range(n):
                matrix[i][j]+=m.mass_kg*sum(v[k][i]*v[k][j] for k in range(3))+sum(w[k][i]*I[k][l]*w[l][j] for k in range(3) for l in range(3))
    if not all(math.isfinite(x) for row in matrix for x in row):
        raise ValueError('Nonfinite reduced inertia')
    return ReducedMassMatrix(*key(reference),members,tuple(tuple(r) for r in matrix))


def physical_tensor_from_entries(entries, *, convention):
    """Convert explicitly declared SI centroidal entries; never infer signs.

    positive_products: diagonal moments, off-diagonals integral(x_i*x_j*dm).
    physical_tensor: entries already use the physical negative-product tensor.
    The consumer must still validate tensor physicality and frame identity.
    """
    if convention not in ('positive_products','physical_tensor'):
        raise ValueError('Explicit known inertia entry convention required')
    if len(entries)!=3 or any(len(row)!=3 for row in entries):
        raise ValueError('A 3x3 centroidal entry matrix is required')
    if not all(math.isfinite(v) for row in entries for v in row):
        raise ValueError('Finite centroidal entries required')
    return tuple(tuple(v*(-1 if convention=='positive_products' and i!=j else 1)
                       for j,v in enumerate(row)) for i,row in enumerate(entries))
