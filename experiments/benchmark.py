# /// script
# requires-python = ">=3.10"
# dependencies = ["tiktoken==0.12.0"]
# ///
"""Compare reader stdout with the same UTF-8 file and check evidence recall."""
import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

READER = Path(__file__).resolve().parents[1] / "plugins/save-my-tokens/skills/focus-output/scripts/focus.py"


def build_log(position):
    lines = [f"INFO stage=compile unit=module_{n:03d} status=ok artifacts=2 elapsed_ms={11+n%23}\n"
             for n in range(260)]
    lines.insert(position, "ERROR build stopped: config key SNAPSHOT_CLOCK missing; failure_code=E7429\n")
    return "".join(lines)


def cases():
    for name, pos in [("early", 3), ("middle", 130), ("late", 257)]:
        yield name, build_log(pos), ["failure_code"], ["SNAPSHOT_CLOCK", "E7429"]
    yield "Korean", ("빌드 작업 완료\n" * 1000 + "검증 거부, 원인=키누락\n" + "배포 대기\n" * 1000), ["거부"], ["키누락"]
    yield "long-line boundary", "x"*16382 + "BOUNDARY=Q19" + "y"*25000, ["BOUNDARY"], ["BOUNDARY=Q19"]
    yield "short", "ERROR missing file\n", [], ["ERROR missing file"]
    yield "unmatched", build_log(130), ["not-in-this-file"], ["no match"]
    # Deliberately ambiguous query. A relevant middle item competes with identical labels.
    yield "dense matches", "".join(f"ERROR item D{n:04d}\n" for n in range(5000)), ["ERROR"], ["D0000", "D1217", "D2500", "D3851", "D4999"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reader", type=Path, default=READER)
    parser.add_argument("--write-log", type=Path, help="write the synthetic middle fixture and exit")
    parser.add_argument("--hdfs", type=Path, help="optional Loghub HDFS_2k.log (pinned in README)")
    args = parser.parse_args()
    if args.write_log:
        args.write_log.write_text(build_log(130), encoding="utf-8")
        return

    import tiktoken
    encoding = tiktoken.get_encoding("o200k_base")
    fixtures = list(cases())
    if args.hdfs:
        data = args.hdfs.read_bytes()
        if hashlib.sha256(data).hexdigest() != "7c967000980c086ed55fa6544ba4f05fe66d44622795e890c68caf8bbb635035":
            parser.error("HDFS file differs from pinned sample")
        fixtures.append(("HDFS", data.decode(), ["blk_-2918118818249673980"],
                         ["10.251.30.85:50010", "/10.251.90.64", "Got exception while serving"]))
    print("fixture | raw tokens | preview tokens | expected markers present")
    with TemporaryDirectory() as directory:
        path = Path(directory) / "sample.txt"
        for name, original, queries, expected in fixtures:
            path.write_bytes(original.encode())
            options = [arg for q in queries for arg in ("-q", q)]
            raw = subprocess.check_output([sys.executable, str(args.reader), str(path), *options])
            output = raw.decode()
            assert len(raw) <= 4096
            found = sum(marker in output for marker in expected)
            if name != "dense matches":
                assert found == len(expected), name
            if name == "short":
                assert output == original
            print(f"{name} | {len(encoding.encode_ordinary(original))} | "
                  f"{len(encoding.encode_ordinary(output))} | {found}/{len(expected)}")


if __name__ == "__main__":
    main()
