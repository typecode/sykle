import os
import copy
import shutil

from jinja2 import Environment
from jinja2.exceptions import TemplateNotFound
from jinja2.loaders import BaseLoader

from anytree import RenderTree, Node, PreOrderIter, find
from anytree.node.util import _repr as node_repr

from sykle.exceptions import PluginException


TEMPLATE_DIR = 'templates'


class RenderingException(PluginException):
    pass


class InvalidExtensionException(RenderingException):
    pass


def flatten_trees(trees):
    return [node for tree in trees for node in tree]


class TemplateRenderer:
    """Coordinates extension and rendering of the base template.

    Much of this class's responsibility is in the dynamic
    composition of template files written in the jinja template
    language. The problem is that we want to keep the templates dry
    and easily composable in the traditional fashion: by extending
    and composing them with block statements. But if they're to be
    optional, it's impossible to know how they should extend each
    other until runtime. To accommodate this condition we build an
    in-memory tree of each template directory, establish a path
    from the base template through each extension template that's
    parallel in it's tree, and prepend each with an "extends" block
    pointing to the parent in its path, all the way back to the base.
    """

    project_base_name = 'project_name'
    app_base_name = 'app_name'
    requirements_file = 'requirements.txt'

    def __init__(self, project_name, base_dir, extensions, app_names=[]):
        self.project_name = project_name
        self.template_dir = os.path.join(base_dir, TEMPLATE_DIR)
        self.extensions = extensions
        self.app_names = app_names

        self.validate_extensions()

        self.base_template_tree = TemplateTree(self.template_dir, 'base')

        self.extension_template_trees = [TemplateTree(
            os.path.join(self.template_dir, ext_type),
            ext_specific
        ) for ext_type, ext_specific in self.extensions]

    def validate_extensions(self):
        for ext_type, ext_specific in self.extensions:
            ext_type_dir = os.path.join(self.template_dir, ext_type)
            ext_specific_dir = os.path.join(ext_type_dir, ext_specific)

            if not (
                os.path.isdir(ext_type_dir) and
                os.path.isdir(ext_specific_dir)
            ):
                msg = 'Extension %s of type %s does not exist' % (
                    ext_specific, ext_type)
                raise InvalidExtensionException(msg)

    def substitute_node_names(self, trees, substitutions, preserve_copy=False):
        nodes = flatten_trees(trees)
        for node in nodes:
            if node.name in substitutions:
                if preserve_copy:
                    original = copy.deepcopy(node)
                    original.parent = node.parent
                node.name = substitutions[node.name]

    def resolve_extension_inheritance(self, base_tree, extension_trees):
        """Establish an (arbitrary) order and successively prepend
        each template with an extends statement. The only necessary
        ordering condition is that the base template be the root of
        each extension path.

        Mutates `base_tree` and `extension_trees`.
        """
        for base_template in base_tree.templates:
            # The node's path sans its root node.
            relative_path = base_template.relative_node_path

            # The first extension will be from the base template.
            extend_from = base_template

            # Walk the extensions in no particular order.
            for tree in extension_trees:
                template = tree.find(rel_path=relative_path)
                if template:
                    # Extend the corresponding template of the extension.
                    # Remove the template node from its tree and make
                    # it a child of the template node that extends it.
                    extend_from.extend(template)

                    # The next extension will be from the current iteree.
                    extend_from = template

        # Make sure any extension templates that don't have a
        # corresponding base template also make it onto the tree.
        for node in flatten_trees(extension_trees):
            if node.root == node:  # node.isroot?
                continue
            if not base_tree.find(rel_path=node.relative_node_path):
                node.parent = base_tree.find(
                    rel_path=node.parent.relative_node_path)

    def resolve_requirements(self, base_tree, extension_trees):
        """Extension requirements files are simply concatenated to the
        base requirements file.
        """
        base_requirements_node = base_tree.find(
            rel_path=self.requirements_file)

        for tree in extension_trees:
            extension_requirements_node = tree.find(
                rel_path=self.requirements_file)

            comment = ' '.join(
                extension_requirements_node.root.name.split('_'))

            tmpl = '{base_requirements}\n# {comment}\n{extension_requirements}\n'

            base_requirements_node.value = tmpl.format(
                base_requirements=base_requirements_node.value,
                comment=comment,
                extension_requirements=extension_requirements_node.value
            )

    def create_app_nodes(self, base_tree, extension_trees):
        """For each <app_name> we've received
              For each tree in base_template_tree + extension_trees
                a) If the tree has an <app_base_name> subtree then
                change that subtree's name to <app_name>.
                b) If we haven't reached the end of <app_names> then
                preserve a copy of the original <app_base_name> subtree
                in the same location.
        """
        for idx, name in enumerate(self.app_names):
            self.substitute_node_names(
                trees=[
                    self.base_template_tree,
                    *self.extension_template_trees
                ],
                substitutions={self.app_base_name: name},
                preserve_copy=idx < len(self.app_names) - 1
            )

    def create_top_dir(self, target):
        if os.path.isdir(target):
            shutil.rmtree(target)
        try:
            os.makedirs(target)
        except FileExistsError:
            raise RenderingException(
                "A '%s' directory already exists" % target)
        except OSError as e:
            raise RenderingException(e)

    def render(self):
        # Filename substitutions need to be applied across all the trees
        # before resolving inheritance so that we don't break node paths.
        self.substitute_node_names(
            [self.base_template_tree, *self.extension_template_trees],
            {self.project_base_name: self.project_name}
        )

        for func in [
            self.create_app_nodes,
            self.resolve_extension_inheritance,
            self.resolve_requirements,
        ]:
            func(
                base_tree=self.base_template_tree,
                extension_trees=self.extension_template_trees
            )

        location = os.path.join(os.getcwd(), self.project_name)
        self.create_top_dir(location)

        context = {
            self.project_base_name: self.project_name,
            'app_names': self.app_names
        }

        environment = Environment(
            loader=TemplateTreeLoader(tree=self.base_template_tree),
            trim_blocks=True,
        )

        try:
            self.base_template_tree.render(location, environment, context)
        except Exception:
            import shutil
            shutil.rmtree(location)
            raise


class TemplateTree:
    """Represent a directory as a tree structure so that we can store
    computed properties of the files (such as their contents) and make
    efficient traversals, comparisons, subtractions, and additions.
    """
    iter_class = PreOrderIter

    def __init__(self, dir, path):
        self.root = TemplateDirNode(path, os_path=dir)
        self._iter = None

        self.build(self.root)

    def __iter__(self):
        self._iter = self.get_iter()
        return self._iter

    def __next__(self):
        if not self._iter:
            self._iter = self.get_iter()
        return next(self._iter)

    def build(self, root):
        for file in os.scandir(root.absolute_os_path):
            if file.name.endswith(('.pyo', '.pyc', '.py.class', '.DS_Store')):
                continue
            node = TemplateNodeFactory(file.name, file.path, parent=root)
            if file.is_dir():
                self.build(node)

    def find(self, abs_path=None, rel_path=None):

        def filter_(node):
            if abs_path:
                return node.absolute_node_path == abs_path
            elif rel_path:
                return node.relative_node_path == rel_path
            else:
                raise Exception('Must specify one of abs_path or rel_path')

        return find(self.root, filter_=filter_)

    def get_iter(self, filter_=None):
        return self.iter_class(
            self.root, filter_=filter_
        )

    @property
    def templates(self):
        return self.get_iter(
            filter_=lambda node: node.is_template
        )

    def render(self, target, environment, context):
        # Skip the root.
        for node in list(self)[1:]:
            node.render(environment, context)
            node.write_to_fs(target)

    def pprint(self):
        print(RenderTree(self.root))


class TemplateNodeFactory:
    def __new__(cls, name, os_path, **kwargs):
        if name.endswith(TemplateNode.template_suffix):
            klass = TemplateNode
        elif os.path.isdir(os_path):
            klass = TemplateDirNode
        else:
            klass = NonTemplateTemplateNode

        return klass(name, os_path, **kwargs)


class BaseTemplateNode(Node):
    is_template = False
    is_dir = False

    def __init__(self, name, os_path, **kwargs):
        super().__init__(name, **kwargs)
        self._os_path = os_path
        self._value = None

        # When nodes are reassigned it's convenient, at the moment
        # only for debugging, to keep track of their original tree.
        # Right now we only reassign them once, so this assignment
        # suffices.
        self._original_root = self.root

    def __repr__(self):
        root = self._original_root or self.root
        arg = '%s../..%s' % (root.name, self.name)
        return node_repr(self, args=[arg], nameblacklist=['name'])

    @property
    def relative_node_path(self):
        if self.is_root:
            return '/'
        return os.path.join(*[node.name for node in self.path[1:]])

    @property
    def absolute_node_path(self):
        return os.path.join(*[node.name for node in self.path])

    @property
    def relative_os_path(self):
        return self.absolute_node_path

    @property
    def absolute_os_path(self):
        return os.path.join(self.root._os_path, self.absolute_node_path)

    @property
    def child(self):
        if self.children:
            return self.children[0]

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    def write_to_fs(self, location, new_path=None):
        path = os.path.join(location, new_path or self.relative_node_path)
        with open(path, 'w', encoding='utf-8') as file:
            file.write(self.value)

    def render(self, *args):
        return


class ValuableTemplateNode(BaseTemplateNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        with open(self._os_path, encoding='utf-8') as file:
            self._value = file.read()


class NonTemplateTemplateNode(ValuableTemplateNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def render(self, *args):
        return


class TemplateDirNode(BaseTemplateNode):
    is_dir = True

    def write_to_fs(self, root):
        path = os.path.join(root, self.relative_node_path)
        os.makedirs(path)


class TemplateNode(ValuableTemplateNode):
    is_template = True
    template_suffix = '.py-tpl'
    template_suffix_rewrite = '.py'

    def extend(self, node):
        """Make `node` a child of `self`. Prepend `node.value` with
        an "extends" block pointing to `self.absolute_node_path`.
        """
        node.parent = self
        node.value = '{{% extends "{path}" %}}\n{value}'.format(
            path=self.absolute_node_path,
            value=node.value
        )

    # Remember that when template nodes are extended they
    # accrue a unary tree of extending children. Since
    # each extends the previous, we only need to render
    # and write the leaf.

    def write_to_fs(self, *args):
        if self.child:
            return

        # On the other hand we want to write to the relative os
        # path of the original base template at the root of that
        # unary tree.
        unary_root = self
        while unary_root.parent.is_template:
            unary_root = unary_root.parent
        path = unary_root.relative_node_path

        # Rewrite '*.py-tpl' -> '*.py'.
        if path.endswith(self.template_suffix):
            path = path[:-len(self.template_suffix)]
            path += self.template_suffix_rewrite

        super().write_to_fs(*args, new_path=path)

    def render(self, environment, context):
        if self.child:
            return

        template = environment.from_string(self.value)
        self.value = template.render(**context)


class TemplateTreeLoader(BaseLoader):
    """Load templates from an in-memory tree, where a path
    in fs format resolves to a node path.
    """
    def __init__(self, tree):
        self.tree = tree

    def get_source(self, environment, template_path):
        node = self.tree.find(abs_path=template_path)

        if not node:
            raise TemplateNotFound(template_path)

        return node.value, None, lambda: True

    def list_templates(self):
        return list(self.tree)
