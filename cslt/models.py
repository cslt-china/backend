from cslt.utils import CsltEnum
from django.db import models
from django.contrib.auth.models import User

from cslt.utils import JSONField


class VideoStatus(CsltEnum):
  WAITING_UPLOAD = 0
  ADMIN_CHECKING = 1
  FORBIDDEN = 2
  DELETED = 3
  SAMPLE = 4
  REJECTED = 5
  PENDING_APPROVAL = 6
  APPROVED = 7


class ScoreType(CsltEnum):
  REVIEW_VIDEO = 1
  CREATE_VIDEO = 2
  CREATE_GLOSS = 3
  VIDEO_QUALITY = 4
  UPLOAD_SAMPLE = 5


class ScoreValue(CsltEnum):
  REVIEW_VIDEO = 1
  CREATE_VIDEO = 3
  CREATE_GLOSS = 1
  APPROVE_VIDEO = 2
  REJECT_VIDEO = 0


class GlossType(CsltEnum):
  SINGLE_WORD = 1
  COMPOSITE_WORD = 2


class Category(models.Model):
  title = models.CharField(max_length=45, blank=True, null=True)
  seq = models.IntegerField(blank=True, null=True)
  parent = models.ForeignKey('self', on_delete=models.SET_DEFAULT,
                             default=None, blank=True,
                             null=True, related_name='children')
  glosses = models.ManyToManyField('Gloss', db_table='cslt_category_gloss')

  class Meta:
    managed = False
    db_table = 'cslt_category'
    verbose_name = 'Category'
    verbose_name_plural = 'Categories'

  def __str__(self):
    full_path = [self.title]
    try:
      k = self.parent
      while k is not None:
        full_path.append(k.title)
        k = k.parent
    except Category.DoesNotExist:
      pass
    return ' / '.join(full_path[::-1])


class Gloss(models.Model):
  text = models.CharField(max_length=45, blank=True, null=False)
  gloss_type = models.IntegerField(
      choices=[(gloss_type, gloss_type.value) for gloss_type in GlossType])
  categories = models.ManyToManyField('Category',
                                      db_table='cslt_category_gloss')

  # Default value for integer field should be 0.
  pending_approval_video_count = models.IntegerField(blank=True, null=True)
  rejected_video_count = models.IntegerField(blank=True, null=True)
  approved_video_count = models.IntegerField(blank=True, null=True)

  sample_video = models.ForeignKey('Video', related_name='sample_video',
                                   on_delete=models.SET_DEFAULT, default=None)
  created_time = models.IntegerField(blank=True)

  duration = models.IntegerField()

  def __str__(self):
    return self.text

  class Meta:
    verbose_name = 'Gloss'
    verbose_name_plural = 'Glosses'
    managed = False
    db_table = 'cslt_gloss'


class Video(models.Model):
  uuid = models.CharField(max_length=36, unique=True)
  user = models.ForeignKey(User, related_name='creator',
                           on_delete=models.SET_DEFAULT, default=None)
  gloss = models.ForeignKey(Gloss,
                            on_delete=models.SET_DEFAULT, default=None)
  review_summary = JSONField(max_length=255, blank=True, default={})
  created_time = models.IntegerField(blank=True)
  video_path = models.FileField(max_length=255, blank=True, null=True)
  thumbnail = models.FileField(max_length=255, blank=True, null=True)
  status = models.IntegerField(
      choices=[(status, status.value) for status in VideoStatus])

  def __str__(self):
    return '{} | {}'.format(self.gloss.text, self.user.username)

  class Meta:
    verbose_name = 'Video'
    verbose_name_plural = 'Videos'
    managed = False
    db_table = 'cslt_video'


class Score(models.Model):
  user = models.ForeignKey(User, related_name='user',
                           on_delete=models.SET_DEFAULT, default=None)
  video = models.ForeignKey(Video, related_name='score',
                            on_delete=models.CASCADE)
  video_owner = models.ForeignKey(User, related_name='video_owner',
                                  on_delete=models.SET_DEFAULT, default=None)
  score_type = models.IntegerField(blank=True, null=True)
  value = models.IntegerField(blank=True, null=True)
  created_time = models.IntegerField(blank=True)

  class Meta:
    managed = False
    db_table = 'cslt_score'
