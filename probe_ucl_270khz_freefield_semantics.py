"""Probe bounded metadata and waveform slices from UCL H115 free-field data."""
from __future__ import annotations
import argparse, json
from datetime import datetime, timezone
from pathlib import Path
import h5py, numpy as np

def text_value(array):
    flat=np.asarray(array).reshape(-1)
    return [x.decode("utf-8","replace") if isinstance(x,(bytes,np.bytes_)) else str(x) for x in flat]
def numeric_summary(array):
    a=np.asarray(array)
    return {"shape":list(a.shape),"dtype":str(a.dtype),"finite":bool(np.isfinite(a).all()),"min":float(np.min(a)),"max":float(np.max(a)),"values":a.reshape(-1).tolist() if a.size<=16 else None,"first_values":a.reshape(-1)[:8].tolist()}
def read_value(ds):
    a=ds[()]
    return {"shape":list(ds.shape),"dtype":str(ds.dtype),"text":text_value(a)} if a.dtype.kind in "SUO" else numeric_summary(a)
def main():
    p=argparse.ArgumentParser(); p.add_argument("input",type=Path); p.add_argument("--output",type=Path,required=True); a=p.parse_args()
    report={"schema_version":"1.0","generated_at_utc":datetime.now(timezone.utc).isoformat(),"policy":"all non-waveform datasets are small enough for bounded metadata inspection; waveformData reads only three complete single-point traces per scan","datasets":{}}
    with h5py.File(a.input,"r") as h:
        for index in range(1,5):
            base=h[f"data/dataset{index}"]; scan=base["scanData"]; drive=base["drivingConditions"]
            coordinates=np.asarray(scan["scanCoordinates"][()])
            points=coordinates.shape[-1]; selected=sorted(set([0,points//2,points-1]))
            wave=scan["waveformData"]
            traces=[]
            for point in selected:
                trace=np.asarray(wave[0,:,point],dtype=np.float64)
                traces.append({"point_index":point,"coordinate":coordinates[0,:,point].tolist(),"samples":trace.size,"finite":bool(np.isfinite(trace).all()),"min":float(trace.min()),"max":float(trace.max()),"rms":float(np.sqrt(np.mean(trace**2))),"first_values":trace[:8].tolist()})
            item={"driving":{},"scan":{},"coordinates":{"shape":list(coordinates.shape),"axis_min":coordinates[0].min(axis=1).tolist(),"axis_max":coordinates[0].max(axis=1).tolist(),"first":coordinates[0,:,0].tolist(),"middle":coordinates[0,:,points//2].tolist(),"last":coordinates[0,:,-1].tolist()},"bounded_waveform_traces":traces}
            for key,ds in drive.items(): item["driving"][key]=read_value(ds)
            for key,ds in scan.items():
                if key not in {"waveformData","scanCoordinates","scanTemperature","waveformTriggerDelay"}: item["scan"][key]=read_value(ds)
            report["datasets"][f"dataset{index}"]=item
        for path in ("medium","project","source/sourceProperties","sensor/sensorProperties"):
            group=h[path]; report[path]={key:read_value(ds) for key,ds in group.items() if isinstance(ds,h5py.Dataset)}
        for path in ("source/signalChain","sensor/signalChain"):
            report[path]={}
            for component,group in h[path].items():
                report[path][component]={key:read_value(ds) for key,ds in group.items() if isinstance(ds,h5py.Dataset)}
        response=np.asarray(h["sensor/sensorProperties/frequencyResponse"][()])
        report["sensor_frequency_response"]={"shape":list(response.shape),"rows":[numeric_summary(response[0,row,:]) for row in range(response.shape[1])]}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(json.dumps({"status":"completed","output":str(a.output),"measurement_datasets":4})); return 0
if __name__=="__main__": raise SystemExit(main())
