
import argparse
from osgeo import gdal

from .workflows.mosaic import mosaic_workflow
from .workflows.timelapse import timelapse_workflow

gdal.AllRegister()

def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    mosaic_workflow.register(subparsers)
    timelapse_workflow.register(subparsers)

    args = parser.parse_args()
    try: 
        args.func(args)
    except AttributeError:
        parser.print_help()


if __name__ == '__main__':
    main()
