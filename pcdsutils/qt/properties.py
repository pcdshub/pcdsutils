import logging

from qtpy import QtCore


logger = logging.getLogger(__name__)

SKIP_TYPENAMES = {'Shadow', 'Shape'}


def get_qt_properties(cls):
    'Yields all QMetaProperty instances from a given class'
    meta_obj = cls.staticMetaObject
    for prop_idx in range(meta_obj.propertyCount()):
        yield meta_obj.property(prop_idx)


class PassthroughProperty(QtCore.Property):
    '''
    A qtpy pass-through property, acting as a proxy of an attribute's property

    Parameters
    ----------
    object_attr_name : str
        The attribute name (e.g., ``'label'`` of ``self.label``)
    property_name : str
        The property name from the object (e.g., ``'text'`` assuming the object
        is a ``QLabel``)
    type_ : str or type
        The type name or type itself (e.g., ``'QString'`` in the case of
        ``'text'``)
    '''

    def __init__(self, object_attr_name: str, property_name: str, type_: str,
                 **kwargs):
        self.object_attr_name = object_attr_name
        self.property_name = property_name
        self.type_ = type_
        super().__init__(type_, self.getter, self.setter, **kwargs)

    def getter(self, instance):
        obj = getattr(instance, self.object_attr_name)
        return obj.property(self.property_name)

    def setter(self, instance, value):
        obj = getattr(instance, self.object_attr_name)
        if not obj.setProperty(self.property_name, value):
            logger.warning('Set property failed: %s.%s = %r',
                           self.object_attr_name, self.property_name,
                           value)

    def __repr__(self):
        return (f'<{self.__class__.__name__} {self.property_name}.'
                f'{self.object_attr_name} {self.type_}>')


class ReadonlyPassthroughProperty(PassthroughProperty):
    setter = None


def forward_properties(locals_dict, attr_name, cls, superclasses, *,
                       prefix=None, predicate=None, designable=True,
                       rw_class=PassthroughProperty,
                       ro_class=ReadonlyPassthroughProperty,
                       ):
    '''
    Forward properties from a QObject attribute in a class given its name

    For use in class definitions. As the usage is somewhat nonstandard, be sure
    to look at the example below.

    Parameters
    ----------
    locals_dict : dict
        Locals for the class (i.e., the dictionary of all things defined above
        in the class body)
    attr_name : str
        The attribute name of the object
    cls : subclass of QObject
        The class type of the attribute
    superclasses : list
        The superclasses of the newly-defined class
    prefix : str, optional
        Prefix the properties with this string. Defaults to ``'{attr_name}_'``
    predicate : callable, optional
        Condition (predicate) for inclusion of the property.  Defaults to
        checking ``isDesignable``
    designable : bool, optional
        Passed to the resulting ``PassthroughProperty``, defaults to True
    rw_class : subclass of ``PassthroughProperty``, optional
        The class to use for a read-write property
    ro_class : subclass of ``PassthroughProperty``, optional
        The class to use for a read-only property

    Returns
    -------
    properties : dict
        A dictionary of properties to be added to the class namespace (see
        example)

    Example
    -------
    For example, if CustomWidget has a QLabel as an attribute 'label', all
    designable properties can be forwarded to the new class using the
    following::

        class CustomWidget(QtWidgets.QFrame):
            def __init__(self, parent=None):
                super().__init__(parent=parent)
                self.label = QtWidgets.QLabel()

            locals().update(**forward_properties(
                locals_dict=locals(),
                attr_name='label',
                cls=QtWidgets.QLabel,
                superclasses=[QtWidgets.QFrame]
            ))

    '''
    if predicate is None:
        def predicate(prop):
            return (prop.isDesignable()
                    and prop.typeName() not in SKIP_TYPENAMES)
    elif isinstance(predicate, (tuple, set, list)):
        allowed_names = predicate

        def predicate(prop):
            return (prop.name() in allowed_names
                    and prop.typeName() not in SKIP_TYPENAMES)
    else:
        if not callable(predicate):
            raise ValueError(
                'predicate must be callable and accept a Property argument')

    supercls_properties = set([
        prop.name()
        for supercls in superclasses
        for prop in get_qt_properties(supercls)
    ])

    prefix = prefix or f'{attr_name}_'
    bad_names = supercls_properties.union(set(locals_dict))
    properties = {
        prop.name(): prop
        for prop in get_qt_properties(cls)
        if (prefix + prop.name()) not in bad_names and predicate(prop)
    }

    passthrough_properties = {}
    for name, prop in properties.items():
        prop_cls = rw_class if prop.isWritable() else ro_class
        try:
            passthrough_properties[prefix + name] = prop_cls(
                object_attr_name=attr_name,
                property_name=name,
                type_=prop.typeName(),
                designable=designable,
                scriptable=prop.isScriptable(),
                stored=prop.isStored(),
                user=prop.isUser(),
                constant=prop.isConstant(),
                final=prop.isFinal(),
            )
        except TypeError as ex:
            # Some types such as SizeConstraint are not supported in PyQt5
            logger.debug('Unable to create %s', prop_cls.__name__, exc_info=ex)

    return passthrough_properties


def forward_property(
        attr_name, cls, prop_name, *,
        designable=None, scriptable=None, stored=None, user=None,
        rw_class=PassthroughProperty, ro_class=ReadonlyPassthroughProperty
        ):
    '''
    Forward one property from a QObject attribute in a class given its name

    For use in class definitions. As the usage is somewhat nonstandard, be sure
    to look at the example below.

    Parameters
    ----------
    attr_name : str
        The attribute name of the object
    cls : subclass of QObject
        The class type of the attribute
    prop_name : str
        The property name of ``cls``
    designable : bool, optional
        Override the designable attribute
    scriptable : bool, optional
        Override the scriptable attribute
    stored : bool, optional
        Override the stored attribute
    user : bool, optional
        Override the user attribute
    rw_class : subclass of ``PassthroughProperty``, optional
        The class to use for a read-write property
    ro_class : subclass of ``PassthroughProperty``, optional
        The class to use for a read-only property

    Returns
    -------
    property : Property
        The forwarded property

    Example
    -------
    For example, if CustomWidget has a QLabel as an attribute 'label', a single
    property of that label can be forwarded to the new class using the
    following::

        class CustomWidget(QtWidgets.QFrame):
            def __init__(self, parent=None):
                super().__init__(parent=parent)
                self.label = QtWidgets.QLabel()

            label_text = forward_property('label', QtWidgets.QLabel, 'text')

    '''
    try:
        prop, = [prop for prop in get_qt_properties(cls)
                 if prop.name() == prop_name]
    except Exception as ex:
        raise AttributeError(f'Unable to get find property {prop_name!r} in '
                             f'{cls.__name__}') from ex

    prop_cls = rw_class if prop.isWritable() else ro_class

    def value_or_default(value, default):
        return value if default is None else default

    return prop_cls(
        object_attr_name=attr_name,
        property_name=prop_name,
        type_=prop.typeName(),
        designable=value_or_default(prop.isDesignable(), designable),
        scriptable=value_or_default(prop.isScriptable(), scriptable),
        stored=value_or_default(prop.isStored(), stored),
        user=value_or_default(prop.isUser(), user),
        constant=prop.isConstant(),
        final=prop.isFinal(),
    )
