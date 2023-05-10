from invoke import Result, task, run
from pathlib import Path
import os
import yaml
from typing import Dict
from datetime import date
"""
Project Structure:

docs/md/ - directory that holds are markdown files of the article

docs/assets/img/ - directory that holds all images

docs/*.html - all final html files

"""

project_path = Path(os.path.realpath(__file__)).parent.parent
html_dir_path = Path(f"{project_path}/docs")
md_dir_path = Path(f"{html_dir_path}/md")
yaml_dir_path = Path(f"{html_dir_path}/yaml")
img_dir_path = Path(f"{html_dir_path}/assets/img")
template_dir_path = Path(f"{html_dir_path}/templates")

class Template:

    background_repl: str = "X BACKGROUND IMG X"
    title_repl: str = "X TITLE X"
    subtitle_repl: str = "X SUBTITLE X"
    date_repl: str = "X DATE X"
    body_repl: str = "X ARTICLE BODY X"
    template_contents: str
    article_body: str
    article_data: Dict[str, str]
    final_contents: str
    html_file_path: Path

    def __init__(self, md_file_path: Path, yaml_file_path: Path, html_file_path: Path, overwrite: bool = False):
        
        with open(f"{template_dir_path.absolute()}/template.html", 'r+') as html_file:
            self.template_contents = html_file.read()
        
        assert len(self.template_contents) > 0, f"{html_dir_path.absolute()}/template.html is empty"
        if not overwrite:
            assert not html_file_path.exists(), f"File {html_file_path} already exists, please choose a non-existing filepath"
        if not md_file_path.exists():
            raise FileNotFoundError(f"File {md_file_path} is not found, please provide an existing filename under {md_dir_path}")
        self.html_file_path = html_file_path

        raw_conversion_results = Template.get_raw_html(md_file_path)
        if raw_conversion_results.return_code != 0:
            raise Exception("Pandoc failed to convert the file")
        
        self.article_body = raw_conversion_results.stdout
        with open(yaml_file_path, 'r+') as yaml_file:
            self.article_data = dict(yaml.safe_load(yaml_file))
        
        assert len(self.article_data) > 0, "Yaml config came out empty! please add to it"
        
        self.final_contents = None
    
    def populate_template(self) -> None:
        self.final_contents = self.template_contents
        bg_image_str = self.article_data.get('background_image')
        assert bg_image_str is not None, "Add 'background_image' field to yaml"
        self.final_contents = self.final_contents.replace(self.background_repl, self.article_data['background_image'])
        
        title_str = self.article_data.get('title')
        assert title_str is not None, "Add 'title' field to yaml"
        self.final_contents = self.final_contents.replace(self.title_repl, title_str)

        subtitle_str = self.article_data.get('subtitle')
        if subtitle_str is None:
            contents_by_line = self.final_contents.split('\n')
            for line_index in range(len(contents_by_line)):
                if self.subtitle_repl in contents_by_line[line_index]:
                    contents_by_line.pop(line_index)
                    break
            self.final_contents = '\n'.join(contents_by_line)
        else:
            self.final_contents = self.final_contents.replace(self.subtitle_repl, subtitle_str)

        self.final_contents = self.final_contents.replace(self.body_repl, self.article_body)

        today = date.today()
        self.final_contents = self.final_contents.replace(self.date_repl, today.strftime("%B %d, %Y"))

    def write_contents(self) -> None:
        with open(self.html_file_path, 'w+') as output_file:
            output_file.write(self.final_contents)

    @staticmethod
    def get_raw_html(md_file_path: Path) -> Result:
        return run(f"pandoc {md_file_path.absolute()}", hide='stdout')

@task
def convert_to_html(c, md_filename: str, overwrite: bool = False):
    md_file_path = Path(f"{md_dir_path}/{md_filename}")
    html_file_path = Path(f"{html_dir_path}/{md_file_path.stem}.html")
    yaml_data_path = Path(f"{yaml_dir_path}/{md_file_path.stem}.yaml")

    template = Template(md_file_path, yaml_data_path, html_file_path, overwrite=overwrite)
    template.populate_template()
    template.write_contents()

@task
def format_html(c, fix: bool = False):
    flags = ['q', 'i']
    if fix:
        flags.append('m')
    else:
        flags.append('e')
    run(f"tidy -{''.join(flags)} {html_dir_path}/*.html")