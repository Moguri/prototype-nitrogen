import imp
import os

try:
    import pman
except ImportError:
    try:
        from . import pman
    except ImportError:
        import blenderpanda.pman as pman


class BasicRenderManager:
    def __init__(self, base):
        import panda3d.core as p3d

        self.base = base
        self.base.render.set_shader_auto()


def create_render_manager(base, config=None):
    if config is None:
        try:
            config = pman.get_config()
        except pman.NoConfigError:
            print("RenderManager: Could not find pman config, falling back to basic plugin")
            config = None

    renderplugin = config.get('general', 'render_plugin') if config else ''

    if not renderplugin:
        return BasicRenderManager(base)

    rppath = pman.get_abs_path(config, renderplugin)
    maindir = os.path.dirname(pman.get_abs_path(config, config.get('run', 'main_file')))
    rppath = os.path.splitext(os.path.relpath(rppath, maindir))[0]
    module_parts = rppath.split(os.sep)

    def load_module(modname, modinfo):
        mod = None
        try:
            mod = imp.load_module(modname, *modinfo)
        finally:
            if modinfo[0]:
                modinfo[0].close()

        return mod
    if pman.is_frozen():
        modname = '.'.join(module_parts)
        modinfo = imp.find_module(modname)
        mod = load_module(modname, modinfo)
    else:
        mod = None
        for modname in module_parts:
            modpath = None if mod is None else mod.__path__
            modinfo = imp.find_module(modname, modpath)
            mod = load_module(modname, modinfo)

    return mod.get_plugin()(base)

