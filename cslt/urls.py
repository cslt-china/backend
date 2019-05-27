from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, re_path, include
from django.views import generic
from rest_framework.schemas import get_schema_view

from cslt.api_views import *
from cslt.views import apk_download
from cslt.admin import StatisticView, GlossesVideoView, GlossesView, \
  GlossesDownloadView

urlpatterns = [
  re_path(r'^$', generic.RedirectView.as_view(url='/api/', permanent=False)),
  re_path(r'^api/$', get_schema_view()),
  re_path(r'^api/auth/', include('rest_framework.urls', namespace='rest_framework')),
  re_path(r'^api/auth/obtain/$', TokenObtainView.as_view()),
  re_path(r'^api/auth/refresh/$', TokenRefreshView.as_view()),
  re_path(r'^api/categories/$', CategoryView.as_view(), name='categories'),
  path('api/categories/<int:id>', CategoryView.as_view(), name='category'),
  path('api/videos/<slug:id>', VideoView.as_view(), name='video'),
  path('api/videos', VideoView.as_view(), name='videos'),
  re_path(r'^api/review/(?P<uuid>[0-9a-f\-]{36})/(?P<action>\b(approve|reject)\b)$', ScoreView.as_view(), name='review-video'),
  path('api/profile/', ProfileView.as_view()),
  #path('api/profile/statics', StatisticView.as_view()),
  path('api/videos/<slug:id>/upload', UploadView.as_view()),
  re_path('api/media/(?P<path>.+)', AuthMediaView.as_view()),
  path('api/bunch/', BunchView.as_view()),
  path('api/glosses/', GlossView.as_view()),
  path('api/glosses/<slug:order>', GlossView.as_view()),
  path('api/dictionary/', DictionaryView.as_view()),
  path('api/account/password', ChangePasswordView.as_view(), name='change_password'),
  path('api/account/agreement', AgreementView.as_view(), name='agreement'),
  # re_path(r'^admin/$', index)
  path('admin/statistic', StatisticView.as_view()),
  path('admin/glosses/download', GlossesDownloadView.as_view()),
  path('admin/glosses/<slug:gloss_id>/video_list', GlossesVideoView.as_view()),
  path('admin/glosses/<slug:gloss_id>/download', GlossesDownloadView.as_view()),
  path('admin/glosses', GlossesView.as_view()),
  path('admin/', admin.site.urls),
  path('apk_download', apk_download)
]

if config.DEBUG:
  urlpatterns = urlpatterns + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
