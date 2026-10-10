from argparse import ArgumentParser
from pathlib import Path
import logging
from .collector import run

def main():
    p=ArgumentParser()
    p.add_argument("--project-dir",type=Path,default=Path("."))
    p.add_argument("--symbols",nargs="+",default=None)
    args=p.parse_args()
    logging.basicConfig(level=logging.INFO)
    status=run(args.project_dir,args.symbols)
    print("Yahoo Finance actual downloads verified:",{k:v["market_date"] for k,v in status["symbols"].items() if v["status"]=="ok"})
if __name__=="__main__":main()
