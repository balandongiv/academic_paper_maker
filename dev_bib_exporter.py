from setting.project_path import project_folder
from grobid_tei_xml.xml_json import run_pipeline

project_review = 'corona_discharge'

# Load project paths
path_dic = project_folder(project_review=project_review)

run_pipeline(path_dic['xml_path'])
