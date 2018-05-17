# -*- coding:utf-8 -*-
import django
from django import template
from django.conf import settings
from django.core.signing import Signer
from django.core.urlresolvers import reverse
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string
from django.utils.crypto import get_random_string

from sorl.thumbnail import get_thumbnail

from .. import default_settings as DEFAULTS
from ..forms import MultiUploadForm
from ..models import MultiuploaderFile

register = template.Library()


if django.get_version() <= '1.5':
    class VerbatimNode(template.Node):
        def __init__(self, text):
            self.text = text

        def render(self, context):
            return self.text

    @register.tag
    def verbatim(parser, token):
        text = []
        while 1:
            token = parser.tokens.pop(0)
            if token.contents == 'endverbatim':
                break
            if token.token_type == template.TOKEN_VAR:
                text.append('{{')
            elif token.token_type == template.TOKEN_BLOCK:
                text.append('{%')
            text.append(token.contents)
            if token.token_type == template.TOKEN_VAR:
                text.append('}}')
            elif token.token_type == template.TOKEN_BLOCK:
                text.append('%}')
        return VerbatimNode(''.join(text))


@register.simple_tag(takes_context=True)
def form_type(context, form_type):
    mu_forms = getattr(settings, "MULTIUPLOADER_FORMS_SETTINGS", DEFAULTS.MULTIUPLOADER_FORMS_SETTINGS)

    signer = Signer()

    if form_type:
        import warnings

        if form_type == '' or form_type not in mu_forms:
            if settings.DEBUG:
                warnings.warn(
                    "A {% form_type %} was used in a template but such form_type (%s) was not provided in settings, default used instead" % form_type)

            return mark_safe(
                u"<div style='display:none'><input type='hidden' name='form_type' value='%s' /></div>" % signer.sign(
                    'default'))

        else:
            return mark_safe(
                u"<div style='display:none'><input type='hidden' name='form_type' value='%s' /></div>" % signer.sign(
                    form_type))
    else:
        # It's very probable that the form_type is missing because of
        # misconfiguration, so we raise a warning

        if settings.DEBUG:
            warnings.warn("A {% form_type %} was used in a template but form_type was not provided")

        return mark_safe(u"")


@register.simple_tag(takes_context=True)
def multiuploader_form(context, form_type="default", template="multiuploader/form.html", target_form_fieldname=None,
        js_prefix="jQuery", send_button_selector=None,
        wrapper_element_id="", lock_while_uploading=True, number_files_attached=0):
    uploaded_files_info = {}
    if context['request'].POST.getlist(target_form_fieldname):
        files = MultiuploaderFile.objects.filter(pk__in=context['request'].POST.getlist(target_form_fieldname))
        for fl in files:
            try:
                im = get_thumbnail(fl.file, "80x80", quality=50)
                thumb_url = im.url
            except Exception as e:
                thumb_url = ''
            if not im.exists():
                thumb_url = ''
            uploaded_files_info[fl.id] = {
                "id": fl.id,
                "name": fl.filename,
                "size": fl.file.size,
                "url": reverse('multiuploader_file_link', args=[fl.pk]),
                "thumbnail_url": thumb_url,
                "delete_url": reverse('multiuploader_delete', args=[fl.pk]),
                "delete_type": "POST",
            }
    return render_to_string(template, {
        'multiuploader_form': MultiUploadForm(form_type=form_type),
        'csrf_token': context["csrf_token"],
        'type': form_type,
        'prefix': js_prefix,
        'send_button_selector': send_button_selector,
        'wrapper_element_id': wrapper_element_id,
        'target_form_fieldname': target_form_fieldname,
        'lock_while_uploading': lock_while_uploading,
        'number_files_attached': number_files_attached,
        'uploaded_files_info': uploaded_files_info,
    })


@register.inclusion_tag('multiuploader/old/noscript.html')
def multiuploader_noscript(uploaded_field=None):
    return {
        'uploaded_widget_html_name': uploaded_field
    }
