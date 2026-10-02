#!/bin/bash
# Full rebuild: DXF, checks, 3D, renders, package. Log in out/run_all.log
cd "$(dirname "$0")"
B=/root/.venvs/blender/bin/python
{
python3 build.py && python3 sheets_png.py
python3 verify.py | grep -E "FAIL|FAILURES|^\[7\]"
python3 dxf_vs_3d.py | tail -1
python3 verify_3d.py | grep -E "FAIL|3D FAILURES"
python3 export_step.py
for m in upholstered frame exploded step-base step-body step-seat step-plate step-prib step-spine export; do
  $B render_blender.py $m 2>&1 | grep -E "^wrote|Error|Traceback"
done
python3 package.py | tail -3
echo RUN_ALL_DONE
} > out/run_all.log 2>&1
