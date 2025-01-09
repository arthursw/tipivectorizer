import argparse
import math
from PIL import Image, ImageOps
from svgpathtools import svg2paths, wsvg
from svgpathtools import Path as SVGPath, Line
from pathlib import Path
from shapely.geometry import Polygon, LineString
from shapely.affinity import scale
import vtracer

def shapely_to_svgpathtools(geometry):
    """Convert a Shapely geometry to an svgpathtools Path."""
    if isinstance(geometry, (Polygon, LineString)):
        coords = list(geometry.exterior.coords) if isinstance(geometry, Polygon) else list(geometry.coords)
        path = SVGPath(*[Line(complex(x1, y1), complex(x2, y2)) for (x1, y1), (x2, y2) in zip(coords[:-1], coords[1:])])
        return path
    return None
  
def inset_polygon(polygon, offset):
    """
    Create an inset (negative buffer) of a polygon.
    Returns None if the resulting shape does not exist.
    """
    if not polygon.is_valid or polygon.is_empty:
        return None

    inset_polygon = polygon.buffer(-offset)
    if inset_polygon.is_empty or inset_polygon.area <= 0:
        return None
    return inset_polygon


def process_svg(svg_path, offset, output_path):
    """Process an SVG file to compute and save inset paths."""
    paths, attributes = svg2paths(svg_path)
    processed_paths = []

    for path in paths:
        # Convert svgpathtools Path to Shapely LineString
        points = [(segment.start.real, segment.start.imag) for segment in path]
        shape = Polygon(points) if len(points) > 2 else LineString(points)

        while True:
            shape = inset_polygon(shape, offset)
            if shape is None:
                break
            processed_path = shapely_to_svgpathtools(shape)
            if processed_path:
                processed_paths.append(processed_path)


    # Save the processed paths as a new SVG
    wsvg(processed_paths, filename=str(output_path))


def raster_to_vector(image_path):
    """Vectorize a raster image using vtracer and return the SVG content."""
    temp_output_path = Path("vectorized.svg")
    vtracer.convert_image_to_svg_py(
        str(image_path),
        str(temp_output_path),
        colormode='color',
        hierarchical='cutout',
        mode='polygon',
        filter_speckle = 4,         # default: 4
        color_precision = 6,        # default: 6
        layer_difference = 16,      # default: 16
        corner_threshold = 60,      # default: 60
        length_threshold = 4.0,     # in [3.5, 10] default: 4.0
        max_iterations = 10,        # default: 10
        splice_threshold = 45,      # default: 45
        path_precision = 8          # default: 8
    )
    return temp_output_path


def process_raster(image_path, offset, output_path):
    """Process a raster image to vectorize, compute insets, and save as SVG."""
    temp_svg_path = raster_to_vector(image_path)
    process_svg(temp_svg_path, offset, output_path)


def main():
    parser = argparse.ArgumentParser(description="Process SVG or raster image for inset paths.")
    parser.add_argument("input", help="Path to the input SVG or raster image.")
    parser.add_argument("-of", "--offset", type=float, default=1.0, help="Inset offset size.")
    parser.add_argument("-o", "--output", help="Path to save the resulting SVG.", required=True)
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if input_path.suffix.lower() in [".svg"]:
        process_svg(input_path, args.offset, output_path)
    elif input_path.suffix.lower() in [".png", ".jpeg", ".jpg"]:
        process_raster(input_path, args.offset, output_path)
    else:
        print("Unsupported file format. Please provide an SVG or raster image.")


if __name__ == "__main__":
    main()
