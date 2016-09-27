from Acquisition import aq_base
from Acquisition import aq_inner
from Acquisition import aq_parent
from datetime import datetime
from dateutil.tz import tzlocal
from OFS.Image import File
from plone.app.caching.operations.utils import getContext
from Products.Archetypes.Field import Image as ImageScale
from Products.CMFCore.FSObject import FSObject
from Products.CMFCore.FSPageTemplate import FSPageTemplate
from Products.CMFCore.interfaces import ICatalogableDublinCore
from Products.ResourceRegistries.interfaces import ICookedFile
from Products.ResourceRegistries.interfaces import IResourceRegistry
from z3c.caching.interfaces import ILastModified
from zope.browserresource.interfaces import IResource
from zope.component import adapter
from zope.component import adapts
from zope.interface import implementer
from zope.interface import Interface
from zope.pagetemplate.interfaces import IPageTemplate


try:
    from zope.dublincore.interfaces import IDCTimes
except ImportError:
    class IDCTimes(Interface):
        pass





@implementer(ILastModified)
@adapter(IPageTemplate)
def PageTemplateDelegateLastModified(template):
    """When looking up an ILastModified for a page template, look up an
    ILastModified for its context. May return None, in which case adaptation
    will fail.
    """
    return ILastModified(template.__parent__, None)

@implementer(ILastModified)
@adapter(FSPageTemplate)
def FSPageTemplateDelegateLastModified(template):
    """When looking up an ILastModified for a page template, look up an
    ILastModified for its context. Must register separately or the FSObject
    adapter would otherwise take precedence.
    """
    return PageTemplateDelegateLastModified(template)

@implementer(ILastModified)
class PersistentLastModified(object):
    """General ILastModified adapter for persistent objects that have a
    _p_mtime. Note that we don't register this for IPersistent, because
    that interface is mixed into too many things and may end up taking
    precedence over other adapters. Instead, this can be registered on an
    as-needed basis with ZCML.
    """

    def __init__(self, context):
        self.context = context

    def __call__(self):
        context = aq_base(self.context)
        mtime = getattr(context, '_p_mtime', None)
        if mtime is not None and mtime > 0:
            return datetime.fromtimestamp(mtime, tzlocal())
        return None

class OFSFileLastModified(PersistentLastModified):
    """ILastModified adapter for OFS.Image.File
    """
    adapts(File)

@implementer(ILastModified)
class ImageScaleLastModified(object):
    """ILastModified adapter for Products.Archetypes.Field.Image
    """
    adapts(ImageScale)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        parent = getContext(self.context)
        if parent is not None:
            return ILastModified(parent)()
        return None

@implementer(ILastModified)
class FSObjectLastModified(object):
    """ILastModified adapter for FSFile and FSImage
    """
    adapts(FSObject)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        # Update from filesystem if we are in debug mode (only)
        self.context._updateFromFS()
        # we do this instead of getModTime() to avoid having to convert from
        # a DateTime
        mtime = self.context._file_mod_time
        return datetime.fromtimestamp(mtime, tzlocal())

@implementer(ILastModified)
class CatalogableDublinCoreLastModified(object):
    """ILastModified adapter for ICatalogableDublinCore, which includes
    most CMF, Archetypes and Dexterity content
    """
    adapts(ICatalogableDublinCore)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        modified = self.context.modified()
        if modified is None:
            return None
        return modified.asdatetime()

@implementer(ILastModified)
class DCTimesLastModified(object):
    """ILastModified adapter for zope.dublincore IDCTimes
    """
    adapts(IDCTimes)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        return self.context.modified

@implementer(ILastModified)
class ResourceLastModified(object):
    """ILastModified for Zope 3 style browser resources
    """
    adapts(IResource)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        lmt = getattr(self.context.context, 'lmt', None)
        if lmt is not None:
            return datetime.fromtimestamp(lmt, tzlocal())
        return None

@implementer(ILastModified)
class CookedFileLastModified(object):
    """ILastModified for Resource Registry `cooked` files
    """
    adapts(ICookedFile)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        registry = getContext(self.context, IResourceRegistry)
        if registry is not None:
            if registry.getDebugMode() or not registry.isCacheable(self.context.__name__):
                return None
            mtime = getattr(registry.aq_base, '_p_mtime', None)
            if mtime is not None and mtime > 0:
                return datetime.fromtimestamp(mtime, tzlocal())
        return None
