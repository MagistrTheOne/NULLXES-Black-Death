# vehicle_attr_lowagl — P2 VehicleAttr pack

**Layout:** `attr_classifier`  
**Datasets:** CompCars / VMMR (ground/low-AGL). **Not** VisDrone for make/model.  
**Mission:** only with `max_agl_m` low (e.g. ≤40) in MissionProfile.  
**Output:** WorldObject.attrs `{make,model,vehicle_type}` or `attr_unknown`.  
**CERBER head:** unchanged (vehicle=1 only).
