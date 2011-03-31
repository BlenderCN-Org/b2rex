import os

import xml.etree.ElementTree as ET

from .info import get_component_info
from .library import library

def attr_name(name):
    return name.lower().replace(' ', '_')

class RexSceneExporter(object):
    def export(self, scene, filename):
        """
        Export the given scene into given filename.
        """
        root = ET.Element('scene')
        self._dirname = os.path.dirname(filename)
        for idx, obj in enumerate(scene.objects):
            self.export_object(obj, root, idx)
        tree = ET.ElementTree(root)
        tree.write(filename)

    def test(self):
        """
        Export current scene to a test file
        """
        import bpy
        self.export(bpy.context.scene, "/tmp/test.xml")

    def export_object(self, obj, root, idx):
        """
        Export the given blender object into a rex element tree
        """
        entity = ET.SubElement(root, 'entity')
        entity.set('id', str(idx))
        self.export_components(obj, entity)

    def export_components(self, obj, entity):
        """
        Export all components from the given object into a
        rex entity element tree.
        """
        components_info = get_component_info()
        for comp in obj.opensim.components:
            component = ET.SubElement(entity, 'component')
            component.set('type', comp.component_type)
            component.set('sync', '1')
            for attr in comp.attribute_names:
                value = getattr(comp, attr_name(attr))
                if comp.component_type in components_info:
                    attr_meta = list(filter(lambda s: list(s.keys())[0] == attr,
                                            components_info[comp.component_type]))
                    if attr_meta:
                        attr_meta = list(attr_meta[0].values())[0]
                else:
                    attr_meta = None

                attribute = ET.SubElement(component, 'attribute')
                if attr_meta:
                    if 'internal_name' in attr_meta:
                        name = attr_meta['internal_name']
                    else:
                        name = attr
                    attr_type = attr_meta['type']
                    if attr_type == 'boolean':
                        value = bool(value)
                    elif attr_type == 'jsscript':
                        comp = library.get_component('jsscript', value)
                        comp.pack(self._dirname)
                        value = 'local://'+value+'.js'
                else:
                    name = attr

                attribute.set('name', name)
                attribute.set('value', self.format_attribute(value))

    def format_attribute(self, value):
        """
        Format the given value for inclusion into rex xml.
        """
        if value.__class__ == bool:
            if value:
                return 'true'
            else:
                return 'false'
        return str(value)
