from django.http import HttpResponse
from django.template import loader


def index(request):
  template = loader.get_template('admin.html')
  return HttpResponse(template.render({}, request))


def apk_download(request):
  template = loader.get_template('mobile_apk.html')
  return HttpResponse(template.render({}, request))
