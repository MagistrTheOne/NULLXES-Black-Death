# Blend MH61 → MH45 between y=1.0 and y=1.875 m

## Rule

For station \(y \in [1.0, 1.875]\):

\[
\eta = \frac{y - 1.0}{1.875 - 1.0}
\]

1. Normalize both airfoils to unit chord.  
2. Resample to same x-stations (cosine spacing).  
3. Interpolate coordinates: \(z = (1-\eta) z_{MH61} + \eta z_{MH45}\).  
4. Scale thickness toward local `t_c_target` if needed (root stretch only on MH61 side).  
5. Scale by local chord from planform; place LE at planform `x_le`.

Implementation later: `02_aerodynamics/scripts/blend_sections.py`.
