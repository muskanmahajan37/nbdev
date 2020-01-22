# AUTOGENERATED! DO NOT EDIT! File to edit: nbs/03_export2html.ipynb (unless otherwise specified).

__all__ = ['HTMLParseAttrs', 'remove_widget_state', 'hide_cells', 'clean_exports', 'treat_backticks',
           'add_jekyll_notes', 'copy_images', 'adapt_img_path', 'remove_hidden', 'find_default_level', 'add_show_docs',
           'remove_fake_headers', 'remove_empty', 'get_metadata', 'ExecuteShowDocPreprocessor', 'execute_nb',
           'write_tmpl', 'write_tmpls', 'nbdev_exporter', 'process_cells', 'process_cell', 'convert_nb',
           'notebook2html', 'convert_md', 'nb_detach_cells']

# Cell
from .imports import *
from .sync import *
from .export import *
from .showdoc import *
from .template import *

from html.parser import HTMLParser
from nbconvert.preprocessors import ExecutePreprocessor, Preprocessor
from nbconvert import HTMLExporter,MarkdownExporter
import traitlets

# Cell
class HTMLParseAttrs(HTMLParser):
    "Simple HTML parser which stores any attributes in `attrs` dict"
    def handle_starttag(self, tag, attrs): self.tag,self.attrs = tag,dict(attrs)

    def attrs2str(self):
        "Attrs as string"
        return ' '.join([f'{k}="{v}"' for k,v in self.attrs.items()])

    def show(self):
        "Tag with updated attrs"
        return f'<{self.tag} {self.attrs2str()} />'

    def __call__(self, s):
        "Parse `s` and store attrs"
        self.feed(s)
        return self.attrs

# Cell
def remove_widget_state(cell):
    "Remove widgets in the output of `cells`"
    if cell['cell_type'] == 'code' and 'outputs' in cell:
        cell['outputs'] = [l for l in cell['outputs']
                           if not ('data' in l and 'application/vnd.jupyter.widget-view+json' in l.data)]
    return cell

# Cell
# Matches any cell that has a `show_doc` or an `#export` in it
_re_cell_to_hide = r's*show_doc\(|^\s*#\s*export\s+|^\s*#\s*hide_input\s+'

# Cell
def hide_cells(cell):
    "Hide inputs of `cell` that need to be hidden"
    if check_re(cell, _re_cell_to_hide):  cell['metadata'] = {'hide_input': True}
    return cell

# Cell
# Matches any line containing an #exports
_re_exports = re.compile(r'^#\s*exports[^\n]*\n')

# Cell
def clean_exports(cell):
    "Remove exports flag from `cell`"
    cell['source'] = _re_exports.sub('', cell['source'])
    return cell

# Cell
def treat_backticks(cell):
    "Add links to backticks words in `cell`"
    if cell['cell_type'] == 'markdown': cell['source'] = add_doc_links(cell['source'])
    return cell

# Cell
_re_nb_link = re.compile(r"""
# Catches any link to a local notebook and keeps the title in group 1, the link without .ipynb in group 2
\[          # Opening [
([^\]]*)    # Catching group for any character except ]
\]\(        # Closing ], opening (
([^http]    # Catching group that must not begin by html (local notebook)
[^\)]*)     # and containing anything but )
.ipynb\)    # .ipynb and closing )
""", re.VERBOSE)

# Cell
_re_block_notes = re.compile(r"""
# Catches any pattern > Title: content with title in group 1 and content in group 2
^\s*>\s*     # > followed by any number of whitespace
([^:]*)      # Catching group for any character but :
:\s*         # : then any number of whitespace
([^\n]*)     # Catching group for anything but a new line character
(?:\n|$)     # Non-catching group for either a new line or the end of the text
""", re.VERBOSE | re.MULTILINE)

# Cell
def _to_html(text):
    return text.replace("'", "&#8217;")

# Cell
def add_jekyll_notes(cell):
    "Convert block quotes to jekyll notes in `cell`"
    _styles = ['note', 'warning', 'tip', 'important']
    def _inner(m):
        title,text = m.groups()
        if title.lower() not in _styles: return f"> {m.groups()[0]}: {m.groups()[1]}"
        return '{% include '+title.lower()+".html content=\'"+_to_html(text)+"\' %}"
    if cell['cell_type'] == 'markdown':
        cell['source'] = _re_block_notes.sub(_inner, cell['source'])
    return cell

# Cell
_re_image = re.compile(r"""
# Catches any image file used, either with `![alt](image_file)` or `<img src="image_file">`
^(!\[           #   Beginning of line (since re.MULTILINE is passed) followed by ![ in a catching group
[^\]]*          #   Anything but ]
\]\()           #   Closing ] and opening (, end of the first catching group
([^\)]*)        #   Catching block with any character but )
(\))            #   Catching group with closing )
|               # OR
^(<img\ [^>]*>)  #   Catching group with <img some_html_code>
""", re.MULTILINE | re.VERBOSE)

_re_image1 = re.compile(r"^<img\ [^>]*>", re.MULTILINE)

# Cell
def _img2jkl(d, h, jekyll=True):
    if not jekyll: return '<img ' + h.attrs2str() + '>'
    if 'width' in d: d['max-width'] = d.pop('width')
    if 'src' in d:   d['file'] = d.pop('src')
    return '{% include image.html ' + h.attrs2str() + ' %}'

# Cell
def copy_images(cell, fname, dest, jekyll=True):
    "Copy images referenced in `cell` from `fname` parent folder to `dest` folder"
    def _rep_src(m):
        grps = m.groups()
        if grps[3] is not None:
            h = HTMLParseAttrs()
            dic = h(grps[3])
            src = dic['src']
            dic['src'] = Config().doc_baseurl + dic['src']
        else: src = grps[1]
        os.makedirs((Path(dest)/src).parent, exist_ok=True)
        shutil.copy(Path(fname).parent/src, Path(dest)/src)
        if grps[3] is not None: return _img2jkl(dic, h, jekyll=jekyll)
        else:  return f"{grps[0]}{Config().doc_baseurl}{grps[1]}{grps[2]}"
    cell['source'] = _re_image.sub(_rep_src, cell['source'])
    return cell

# Cell
def _relative_to(path1, path2):
    p1,p2 = Path(path1).absolute().parts,Path(path2).absolute().parts
    i=0
    while i <len(p1) and i<len(p2) and p1[i] == p2[i]: i+=1
    p1,p2 = p1[i:],p2[i:]
    return os.path.sep.join(['..' for _ in p2] + list(p1))

# Cell
def adapt_img_path(cell, fname, dest, jekyll=True):
    "Adapt path of images referenced in `cell` from `fname` to work in folder `dest`"
    def _rep(m):
        gps = m.groups()
        if gps[0] is not None:
            start,img,end = gps[:3]
            new_img = _relative_to(fname.parent/img, dest)
            return f'{start}{new_img}{end}'
        else:
            h = HTMLParseAttrs()
            dic = h(gps[3])
            dic['src'] = _relative_to(fname.parent/dic['src'], dest)
            return _img2jkl(dic, h, jekyll=jekyll)
    if cell['cell_type'] == 'markdown': cell['source'] = _re_image.sub(_rep, cell['source'])
    return cell

# Cell
#Matches any cell with #hide or #default_exp or #default_cls_lvl
_re_cell_to_remove = re.compile(r'^\s*#\s*(hide|default_exp|default_cls_lvl)\s+')

# Cell
def remove_hidden(cells):
    "Remove in `cells` the ones with a flag `#hide`, `#default_exp` or `#default_cls_lvl`"
    return [c for c in cells if _re_cell_to_remove.search(c['source']) is None]

# Cell
_re_default_cls_lvl = re.compile(r"""
^               # Beginning of line (since re.MULTILINE is passed)
\s*\#\s*        # Any number of whitespace, #, any number of whitespace
default_cls_lvl # default_cls_lvl
\s*             # Any number of whitespace
(\d*)           # Catching group for any number of digits
\s*$            # Any number of whitespace and end of line (since re.MULTILINE is passed)
""", re.IGNORECASE | re.MULTILINE | re.VERBOSE)

# Cell
def find_default_level(cells):
    "Find in `cells` the default class level."
    for cell in cells:
        tst = check_re(cell, _re_default_cls_lvl)
        if tst: return int(tst.groups()[0])
    return 2

# Cell
#Find a cell with #export(s)
_re_export = re.compile(r'^\s*#\s*exports?\s*', re.IGNORECASE | re.MULTILINE)
_re_show_doc = re.compile(r"""
# First one catches any cell with a #export or #exports, second one catches any show_doc and get the first argument in group 1
show_doc     # show_doc
\s*\(\s*     # Any number of whitespace, opening (, any number of whitespace
([^,\)\s]*)  # Catching group for any character but a comma, a closing ) or a whitespace
[,\)\s]      # A comma, a closing ) or a whitespace
""", re.MULTILINE | re.VERBOSE)

# Cell
def _show_doc_cell(name, cls_lvl=None):
    return {'cell_type': 'code',
            'execution_count': None,
            'metadata': {},
            'outputs': [],
            'source': f"show_doc({name}{'' if cls_lvl is None else f', default_cls_level={cls_lvl}'})"}

def add_show_docs(cells, cls_lvl=None):
    "Add `show_doc` for each exported function or class"
    documented = [_re_show_doc.search(cell['source']).groups()[0] for cell in cells
                  if cell['cell_type']=='code' and _re_show_doc.search(cell['source']) is not None]
    res = []
    for cell in cells:
        res.append(cell)
        if check_re(cell, _re_export):
            names = export_names(cell['source'], func_only=True)
            for n in names:
                if n not in documented: res.append(_show_doc_cell(n, cls_lvl=cls_lvl))
    return res

# Cell
_re_fake_header = re.compile(r"""
# Matches any fake header (one that ends with -)
\#+    # One or more #
\s+    # One or more of whitespace
.*     # Any char
-\s*   # A dash followed by any number of white space
$      # End of text
""", re.VERBOSE)

# Cell
def remove_fake_headers(cells):
    "Remove in `cells` the fake header"
    return [c for c in cells if c['cell_type']=='code' or _re_fake_header.search(c['source']) is None]

# Cell
def remove_empty(cells):
    "Remove in `cells` the empty cells"
    return [c for c in cells if len(c['source']) >0]

# Cell
_re_title_summary = re.compile(r"""
# Catches the title and summary of the notebook, presented as # Title > summary, with title in group 1 and summary in group 2
^\s*       # Beginning of text followe by any number of whitespace
\#\s+      # # followed by one or more of whitespace
([^\n]*)   # Catching group for any character except a new line
\n+        # One or more new lines
>[ ]*       # > followed by any number of whitespace
([^\n]*)   # Catching group for any character except a new line
""", re.VERBOSE)

_re_properties = re.compile(r"""
^-\s+      # Beginnig of a line followed by - and at least one space
(.*?)      # Any pattern (shortest possible)
\s*:\s*    # Any number of whitespace, :, any number of whitespace
(.*?)$     # Any pattern (shortest possible) then end of line
""", re.MULTILINE | re.VERBOSE)

# Cell
def get_metadata(cells):
    "Find the cell with title and summary in `cells`."
    for i,cell in enumerate(cells):
        if cell['cell_type'] == 'markdown':
            match = _re_title_summary.match(cell['source'])
            if match:
                cells.pop(i)
                attrs = {k:v for k,v in _re_properties.findall(cell['source'])}
                return {'keywords': 'fastai',
                        'summary' : match.groups()[1],
                        'title'   : match.groups()[0],
                        **attrs}

    return {'keywords': 'fastai',
            'summary' : 'summary',
            'title'   : 'Title'}

# Cell
_re_cell_to_execute = ReLibName(r"^\s*show_doc\(([^\)]*)\)|^from LIB_NAME\.", re.MULTILINE)

# Cell
class ExecuteShowDocPreprocessor(ExecutePreprocessor):
    "An `ExecutePreprocessor` that only executes `show_doc` and `import` cells"
    def preprocess_cell(self, cell, resources, index):
        if 'source' in cell and cell['cell_type'] == "code":
            if _re_cell_to_execute.re.search(cell['source']):
                return super().preprocess_cell(cell, resources, index)
        return cell, resources

# Cell
def _import_show_doc_cell(mod=None):
    "Add an import show_doc cell."
    source = f"#export\nfrom nbdev.showdoc import show_doc"
    if mod:  source += f"\nfrom {Config().lib_name}.{mod} import *"
    return {'cell_type': 'code',
            'execution_count': None,
            'metadata': {'hide_input': True},
            'outputs': [],
            'source': source}

def execute_nb(nb, mod=None, metadata=None, show_doc_only=True):
    "Execute `nb` (or only the `show_doc` cells) with `metadata`"
    nb['cells'].insert(0, _import_show_doc_cell(mod))
    ep_cls = ExecuteShowDocPreprocessor if show_doc_only else ExecutePreprocessor
    ep = ep_cls(timeout=600, kernel_name='python3')
    metadata = metadata or {}
    pnb = nbformat.from_dict(nb)
    ep.preprocess(pnb, metadata)
    return pnb

# Cell
def write_tmpl(tmpl, nms, cfg, dest):
    "Write `tmpl` to `dest` (if missing) filling in `nms` in template using dict `cfg`"
    if dest.exists(): return
    vs = {o:cfg.d[o] for o in nms.split()}
    outp = tmpl.format(**vs)
    dest.write_text(outp)

# Cell
def write_tmpls():
    "Write out _config.yml and _data/topnav.yml using templates"
    cfg = Config()
    write_tmpl(config_tmpl, 'user lib_name title copyright description', cfg, cfg.doc_path/'_config.yml')
    write_tmpl(topnav_tmpl, 'user lib_name', cfg, cfg.doc_path/'_data'/'topnav.yml')
    write_tmpl(makefile_tmpl, 'nbs_path lib_name', cfg, cfg.config_file.parent/'Makefile')

# Cell
def nbdev_exporter(cls=HTMLExporter, template_file=None):
    cfg = traitlets.config.Config()
    exporter = cls(cfg)
    exporter.exclude_input_prompt=True
    exporter.exclude_output_prompt=True
    exporter.template_file = 'jekyll.tpl' if template_file is None else template_file
    exporter.template_path.append(str(Path(__file__).parent/'templates'))
    return exporter

# Cell
process_cells = [remove_fake_headers, remove_hidden, remove_empty]
process_cell  = [hide_cells, remove_widget_state, add_jekyll_notes]

# Cell
_re_digits = re.compile(r'^\d+\S*?_')

# Cell
def _nb2htmlfname(nb_path, dest=None):
    if dest is None: dest = Config().doc_path
    return Path(dest)/_re_digits.sub('', nb_path.with_suffix('.html').name)

# Cell
def convert_nb(fname, cls=HTMLExporter, template_file=None, exporter=None, dest=None):
    "Convert a notebook `fname` to html file in `dest_path`."
    fname = Path(fname).absolute()
    nb = read_nb(fname)
    meta_jekyll = get_metadata(nb['cells'])
    meta_jekyll['nb_path'] = str(fname.relative_to(Config().lib_path.parent))
    cls_lvl = find_default_level(nb['cells'])
    mod = find_default_export(nb['cells'])
    nb['cells'] = compose(*process_cells,partial(add_show_docs, cls_lvl=cls_lvl))(nb['cells'])
    nb['cells'] = [compose(partial(copy_images, fname=fname, dest=Config().doc_path), *process_cell, treat_backticks)(c)
                    for c in nb['cells']]
    nb = execute_nb(nb, mod=mod)
    nb['cells'] = [clean_exports(c) for c in nb['cells']]
    if exporter is None: exporter = nbdev_exporter(cls=cls, template_file=template_file)
    with open(_nb2htmlfname(fname, dest=dest),'w') as f:
        f.write(exporter.from_notebook_node(nb, resources=meta_jekyll)[0])

# Cell
def _notebook2html(fname, cls=HTMLExporter, template_file=None, exporter=None, dest=None):
    time.sleep(random.random())
    print(f"converting: {fname}")
    try: convert_nb(fname, cls=cls, template_file=template_file, exporter=exporter, dest=dest)
    except Exception as e: print(e)

# Cell
def notebook2html(fname=None, force_all=False, n_workers=None, cls=HTMLExporter, template_file=None, exporter=None, dest=None):
    "Convert all notebooks matching `fname` to html files"
    if fname is None:
        files = [f for f in Config().nbs_path.glob('*.ipynb') if not f.name.startswith('_')]
    else: files = glob.glob(fname)
    if len(files)==1:
        force_all = True
        if n_workers is None: n_workers=0
    if not force_all:
        # only rebuild modified files
        files,_files = [],files.copy()
        for fname in _files:
            fname_out = _nb2htmlfname(Path(fname).absolute())
            if not fname_out.exists() or os.path.getmtime(fname) >= os.path.getmtime(fname_out):
                files.append(fname)
    if len(files)==0: print("No notebooks were modified")
    else: parallel(_notebook2html, files, n_workers=n_workers, cls=cls, template_file=template_file, exporter=exporter, dest=dest)

# Cell
def convert_md(fname, dest_path, img_path='docs/images/', jekyll=True):
    "Convert a notebook `fname` to a markdown file in `dest_path`."
    fname = Path(fname).absolute()
    if not img_path: img_path = fname.stem + '_files/'
    print(img_path)
    Path(img_path).mkdir(exist_ok=True, parents=True)
    nb = read_nb(fname)
    meta_jekyll = get_metadata(nb['cells'])
    try: meta_jekyll['nb_path'] = str(fname.relative_to(Config().lib_path.parent))
    except: meta_jekyll['nb_path'] = str(fname)
    nb['cells'] = compose(*process_cells)(nb['cells'])
    nb['cells'] = [compose(partial(adapt_img_path, fname=fname, dest=dest_path, jekyll=jekyll), *process_cell)(c)
                   for c in nb['cells']]
    fname = Path(fname).absolute()
    dest_name = fname.with_suffix('.md').name
    exp = nbdev_exporter(cls=MarkdownExporter, template_file='jekyll-md.tpl' if jekyll else 'md.tpl')
    export = exp.from_notebook_node(nb, resources=meta_jekyll)
    md = export[0]
    for ext in ['png', 'svg']:
        md = re.sub(r'!\['+ext+'\]\((.+)\)', '!['+ext+'](' + img_path + '\\1)', md)
    with (Path(dest_path)/dest_name).open('w') as f: f.write(md)
    for n,o in export[1]['outputs'].items():
            with open(Path(dest_path)/img_path/n, 'wb') as f: f.write(o)

# Cell
def _nb_detach_cell(cell, dest):
    att,src = cell['attachments'],cell['source']
    mime,img = first(first(att.values()).items())
    ext = mime.split('/')[1]
    for i in range(99999):
        p = dest/(f'att_{i:05d}.{ext}')
        if not p.exists(): break
    p.write_bytes(b64decode(img))
    del(cell['attachments'])
    return [re.sub('attachment:image.png', str(p), o) for o in src]

# Cell
def nb_detach_cells(path_nb, dest=None, replace=True):
    "Export cell attachments to `dest` and update references"
    path_nb = Path(path_nb)
    if not dest: dest = f'{path_nb.stem}_files'
    dest = Path(dest)
    dest.mkdir(exist_ok=True, parents=True)
    j = json.load(path_nb.open())
    atts = [o for o in j['cells'] if 'attachments' in o]
    for o in atts: o['source'] = _nb_detach_cell(o, dest)
    if atts and replace: json.dump(j, path_nb.open('w'))
    if not replace: return j