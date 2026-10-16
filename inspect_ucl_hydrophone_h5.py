"""Write a metadata-only schema inventory for a UCL hydrophone HDF5 file."""
from __future__ import annotations
import argparse, hashlib, json
from datetime import datetime, timezone
from pathlib import Path
import h5py

def digest(path: Path, algorithm: str) -> str:
    h=hashlib.new(algorithm)
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def simple(value):
    if hasattr(value,"tolist"): value=value.tolist()
    if isinstance(value,bytes): return value.decode("utf-8","replace")
    if isinstance(value,(str,int,float,bool)) or value is None: return value
    if isinstance(value,list): return [simple(v) for v in value[:32]]
    return str(value)
def main():
    p=argparse.ArgumentParser(); p.add_argument("input",type=Path); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    datasets=[]; groups=[]
    with h5py.File(a.input,"r") as h:
        root_attrs={k:simple(v) for k,v in h.attrs.items()}
        def visit(name,obj):
            attrs={k:simple(v) for k,v in obj.attrs.items()}
            if isinstance(obj,h5py.Dataset): datasets.append({"path":"/"+name,"shape":list(obj.shape),"dtype":str(obj.dtype),"size":int(obj.size),"compression":obj.compression,"chunks":list(obj.chunks) if obj.chunks else None,"attributes":attrs})
            elif isinstance(obj,h5py.Group): groups.append({"path":"/"+name,"attributes":attrs})
        h.visititems(visit)
    report={"schema_version":"1.0","generated_at_utc":datetime.now(timezone.utc).isoformat(),"source":{"path":str(a.input.resolve()),"size_bytes":a.input.stat().st_size,"md5":digest(a.input,"md5"),"sha256":digest(a.input,"sha256"),"dataset_doi":"10.5522/04/28025240.v2","license":"CC BY 4.0"},"inspection_policy":"metadata only; no full dataset arrays loaded","root_attributes":root_attrs,"groups":groups,"datasets":datasets,"counts":{"groups":len(groups),"datasets":len(datasets)},"next_gate":"Map coordinate, pressure, time, pulse-mode and calibration datasets before any simulation or quantitative comparison."}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps({"status":"completed","groups":len(groups),"datasets":len(datasets),"output":str(a.output)})); return 0
if __name__=="__main__": raise SystemExit(main())
