"""Run a contributor's Blender-Python project INSIDE Blender and report the outcome.

Invoked as:  <blender> --background --factory-startup --python blender_exec.py -- <code.py> <out.json>
Writes {status, error, mesh_objects, verts} to <out.json>. status:
  ok | no_geometry (ran but produced no mesh) | error (raised). The script is expected
  to be self-contained and to build its object when run (the dataset scripts call main()).
"""

import json
import sys
import traceback

import bpy  # noqa: provided by Blender


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    code_path, out_path = argv[0], argv[1]
    result = {"status": "ok", "error": "", "mesh_objects": 0, "verts": 0}
    try:
        src = open(code_path).read()
        exec(compile(src, code_path, "exec"), {"__name__": "__main__", "__file__": code_path})
        meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        verts = sum(len(o.data.vertices) for o in meshes if o.data)
        result["mesh_objects"] = len(meshes)
        result["verts"] = verts
        if verts == 0:
            result["status"] = "no_geometry"
    except BaseException:  # SystemExit too — a script that sys.exit()s isn't "ok"
        result["status"] = "error"
        tb = traceback.format_exc().strip().splitlines()
        result["error"] = (tb[-1] if tb else "unknown")[:300]
    with open(out_path, "w") as fh:
        json.dump(result, fh)


main()
