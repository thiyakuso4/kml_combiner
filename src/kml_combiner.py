import streamlit as st
import fiona
import geopandas as gpd
import tempfile
from shapely.ops import unary_union

# Add KML and LIBKML driver if not present
if "KML" not in fiona.supported_drivers:
    fiona.supported_drivers["KML"] = "rw"  # Enable read/write support for KML
if "LIBKML" not in fiona.supported_drivers:
    fiona.supported_drivers['LIBKML'] = 'rw'

# Streamlit app layout
st.title("KML Combiner Tool")
st.write("Upload inclusion and exclusion KML files to create a combined output.")

# File upload widgets
inclusion_file = st.file_uploader("Drag 'Inclusion' KML here", type=["kml"])
exclusion_file = st.file_uploader("Drag 'Exclusion' KML here", type=["kml"])


# Function to clean geometries
def clean_geometries(gdf):
    gdf["geometry"] = gdf["geometry"].apply(lambda geom: geom.buffer(0) if not geom.is_valid else geom)
    return gdf

if inclusion_file and exclusion_file:
    st.success("Files uploaded successfully!")
    
    if st.button("Combine KMLs"):
        try:
            with st.spinner('Processing...'):
                # Load KMLs as GeoDataFrames
                inclusion_gdf = gpd.read_file(inclusion_file)
                exclusion_gdf = gpd.read_file(exclusion_file)
                # Check files are valid
                if inclusion_gdf.empty:
                    st.error("Inclusion KML file is empty or invalid.")
                    st.stop()
                if exclusion_gdf.empty:
                    st.error("Exclusion KML file is empty or invalid.")
                    st.stop()
                if not all(inclusion_gdf.is_valid):
                    st.warning("Some geometries in the 'Inclusion' KML are invalid. These will be corrected.")
                if not all(exclusion_gdf.is_valid):
                    st.warning("Some geometries in the 'Exclusion' KML are invalid. These will be corrected.")

                # Clean inclusion and exclusion geometries
                inclusion_gdf = clean_geometries(inclusion_gdf)
                exclusion_gdf = clean_geometries(exclusion_gdf)
                
                # Reproject exclusion file, if inclusion CRS is not same as exclusion CRS
                if inclusion_gdf.crs != exclusion_gdf.crs:
                    try:
                        exclusion_gdf = exclusion_gdf.to_crs(inclusion_gdf.crs)
                    except Exception as e:
                        st.error(f"Inclusion and exclusion file are not having same projection and error while reprojecting: {e}")
                        st.stop()

                # Get the union of exclusion geometries
                exclusion_union = unary_union(exclusion_gdf.geometry)

                # Compute the difference for each geometry in inclusion_gdf
                inclusion_gdf["geometry"] = inclusion_gdf.geometry.apply(lambda geom: geom.difference(exclusion_union))
                
                
                # Save the result to a KML file
                # output_path = "combined.kml"
                # inclusion_gdf.to_file(output_path, driver="KML")
                
                # Create a unique temporary file path for output KML to avoid conflicts
                with tempfile.NamedTemporaryFile(delete=False, suffix=".kml") as tmpfile:
                    output_path = tmpfile.name
                    inclusion_gdf.to_file(output_path, driver="KML")
                
                # Allow user to download the combined KML
                with open(output_path, "rb") as f:
                    st.download_button(
                        label="Download Combined KML",
                        data=f,
                        file_name="combined.kml",
                        mime="application/vnd.google-earth.kml+xml"
                    )
        except Exception as e:
            st.error(f"An error occurred: {e}")
            st.stop()
