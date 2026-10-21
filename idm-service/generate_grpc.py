from pathlib import Path

from grpc_tools import protoc

PROTO_DIR = Path(__file__).resolve().parent.parent / "proto"
OUTPUT_DIR = Path(__file__).resolve().parent

exit_code = protoc.main([
    "grpc_tools.protoc",
    f"--proto_path={PROTO_DIR}",
    f"--python_out={OUTPUT_DIR}",
    f"--grpc_python_out={OUTPUT_DIR}",
    str(PROTO_DIR / "idm.proto"),
])

if exit_code != 0:
    raise SystemExit(f"Compilarea idm.proto a esuat (cod {exit_code})")
print(f"Generat idm_pb2.py si idm_pb2_grpc.py in {OUTPUT_DIR}")
