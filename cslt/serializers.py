import logging
import os.path
import uuid

from django.core.files.base import ContentFile
from rest_framework import serializers
import datetime
from cslt import settings
from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)

def get_upload_url(file_name):
  ext = os.path.splitext(file_name)

  dir = os.path.join(datetime.date.today().strftime('%Y-%m'))
  name = str(uuid.uuid4())
  return os.path.join(dir, name + ext[1])

class SimpleCategorySerializer(serializers.Serializer):
  id = serializers.IntegerField()
  title = serializers.CharField()


class SimpleUserSerializer(serializers.Serializer):
  id = serializers.IntegerField()
  username = serializers.CharField()


class SimpleVideoSerializer(serializers.Serializer):
  uuid = serializers.CharField(max_length=36)
  video_path = serializers.CharField()
  thumbnail = serializers.CharField()
  creator = SimpleUserSerializer(source='user')


class VideoSerializer(serializers.Serializer):
  id = serializers.IntegerField(write_only=True)
  uuid = serializers.CharField()
  creator = SimpleUserSerializer(source='user')
  gloss_id = serializers.IntegerField(source='gloss.id', read_only=True)
  gloss_text = serializers.CharField(source='gloss.text', read_only=True)
  created_time = serializers.IntegerField()
  video_path = serializers.CharField()
  thumbnail = serializers.CharField()
  status = serializers.IntegerField()
  review_summary = serializers.DictField()


class VideoUploadSerializer(serializers.Serializer):
  uuid = serializers.CharField()
  user_id = serializers.IntegerField()
  video = serializers.FileField()
  thumbnail = serializers.FileField()

  def create(self, validated_data):
    video = validated_data['video']

    if video.content_type != 'video/mp4':
      raise Exception('The uploaded file is not supported ' + video.content_type)
    file_path = get_upload_url(video.name)
    try:
      path = default_storage.save(file_path, video)
      path = os.path.join(settings.MEDIA_URL, path)
      self.validated_data['video'] = path

    except Exception as e:
      logger.error(e)

    thumb = validated_data['thumbnail']
    if thumb.content_type != 'image/png':
      raise Exception('The uploaded file is not supported')

    file_path = get_upload_url(thumb.name)
    try:
      path = default_storage.save(file_path, thumb)
      path = os.path.join(settings.MEDIA_URL, path)
      self.validated_data['thumbnail'] = path
    except Exception as e:
      logger.error(e)

    return self

  class Meta:
    fields = ('uuid', 'user_id', 'video', 'thumbnail')


class GlossSerializer(serializers.Serializer):
  id = serializers.IntegerField()
  text = serializers.CharField()
  gloss_type = serializers.IntegerField()
  sample_video = VideoSerializer()
  # The sum of the following three video counts should be
  # equal to the total number of video samples submitted to
  # the server.
  pending_approval_video_count = serializers.IntegerField()
  rejected_video_count = serializers.IntegerField()
  approved_video_count = serializers.IntegerField()
  categories = SimpleCategorySerializer(many=True)
  created_time = serializers.IntegerField()
  duration = serializers.IntegerField()


class ChangePasswordSerializer(serializers.Serializer):
  """
  Serializer for password change endpoint.
  """
  old_password = serializers.CharField(required=True)
  new_password = serializers.CharField(required=True)


class CategorySerializer(serializers.Serializer):
  id = serializers.IntegerField()
  title = serializers.CharField()
  children = SimpleCategorySerializer(many=True)
  glosses = GlossSerializer(many=True)


class UserScoreSerializer(serializers.Serializer):
  user_id = serializers.IntegerField()
  review_video_score = serializers.IntegerField()
  review_video_count = serializers.IntegerField()
  create_video_score = serializers.IntegerField()
  create_video_count = serializers.IntegerField()
  create_gloss_score = serializers.IntegerField()
  create_gloss_count = serializers.IntegerField()
  verify_video_score = serializers.IntegerField()
  verify_video_count = serializers.IntegerField()
  video_quality_score = serializers.IntegerField()
  video_quality_count = serializers.IntegerField()


class ReviewScoreSerializer(serializers.Serializer):
  uuid = serializers.CharField()
  video_score = serializers.IntegerField()
  user_score = serializers.IntegerField()
