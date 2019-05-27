from datetime import datetime

from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import HttpResponse
from django.template import loader
from django.views import View

from cslt import config, settings
from cslt.serializers import VideoSerializer
from .models import Video, Gloss, Category, Score, VideoStatus


admin.site.register(Video)
admin.site.register(Gloss)
admin.site.register(Category)


class StatisticView(View):
  def get(self, request):
    template = loader.get_template('statistic.html')

    user_stats = User.objects.raw('SELECT auth_user.id, username, COUNT(cslt_video.id) as total_count FROM `cslt_video` JOIN auth_user ON auth_user.id = cslt_video.user_id WHERE cslt_video.status > 4 GROUP BY user_id;')
    result = {o.id: o.__dict__ for o in user_stats}

    user_stats = User.objects.raw('SELECT auth_user.id, username, COUNT(cslt_video.id) as total_count FROM `cslt_video` JOIN auth_user ON auth_user.id = cslt_video.user_id WHERE cslt_video.status = 6 GROUP BY user_id;')
    for o in user_stats:
      result[o.id]['pending_count'] = o.total_count
    user_stats = User.objects.raw('SELECT auth_user.id, username, COUNT(cslt_video.id) as total_count FROM `cslt_video` JOIN auth_user ON auth_user.id = cslt_video.user_id WHERE cslt_video.status = 7 GROUP BY user_id;')
    for o in user_stats:
      result[o.id]['approved_count'] = o.total_count
    user_stats = User.objects.raw('SELECT auth_user.id, username, COUNT(cslt_video.id) as total_count FROM `cslt_video` JOIN auth_user ON auth_user.id = cslt_video.user_id WHERE cslt_video.status = 5 GROUP BY user_id;')
    for o in user_stats:
      result[o.id]['rejected_count'] = o.total_count

    daily_stats = Video.objects.raw("SELECT 1 as id, from_unixtime(cslt_video.created_time, '%%Y-%%m-%%d') as `date`, COUNT(cslt_video.id) FROM `cslt_video` WHERE cslt_video.status > 0 GROUP BY `date`")
    daily_stats = [o.__dict__ for o in daily_stats]

    score_stats = []
    for id in result.keys():
      scores = Score.objects.raw('''
        SELECT 1 as id, `cslt_score`.`score_type`, SUM(`cslt_score`.`value`) AS `total`, COUNT(`cslt_score`.`value`) AS `count` 
          FROM `cslt_score` INNER JOIN `cslt_video` ON (`cslt_score`.`video_id` = `cslt_video`.`id`) 
          INNER JOIN `cslt_gloss` ON (`cslt_video`.`gloss_id` = `cslt_gloss`.`id`) 
          WHERE (`cslt_gloss`.`gloss_type` <> 0 AND ((`cslt_score`.`user_id` = {0} AND NOT (`cslt_score`.`score_type` = 4 AND `cslt_score`.`score_type` IS NOT NULL)) 
            OR (`cslt_score`.`video_owner_id` = {0} AND `cslt_score`.`score_type` = 4))) 
          GROUP BY `cslt_score`.`score_type` ORDER BY `cslt_score`.`score_type`;'''.format(id))
      score_map = {o.score_type: o.total for o in scores}
      score_stats.append({
        'username': result[id]['username'],
        'created_video_score': score_map[2] if 2 in score_map else 0,
        'approved_video_score': score_map[4] if 4 in score_map else 0,
        'review_video_score': score_map[1] if 1 in score_map else 0,
        'total_score': sum(score_map.values())
      })

    return HttpResponse(template.render({
      'user_stats': result.values(),
      'daily_stats': daily_stats,
      'score_stats': score_stats
    }, request))


class GlossesView(View):
  def get(self, request):
    glosses = Gloss.objects.filter(~Q(gloss_type=0)).order_by('text')
    template = loader.get_template('gloss_list.html')
    return HttpResponse(template.render({
      'glosses': glosses
    }, request))


class GlossesVideoView(View):
  def get(self, request, gloss_id):
    videos = Video.objects.select_related('user').filter(gloss_id=gloss_id, status__gt=VideoStatus.SAMPLE)

    video_serializer = VideoSerializer(videos, many=True)
    result = {
      'approved_videos': [x for x in video_serializer.data if x['status'] == VideoStatus.APPROVED.value],
      'rejected_videos': [x for x in video_serializer.data if x['status'] == VideoStatus.REJECTED.value],
      'pending_approval_videos': [x for x in video_serializer.data if x['status'] == VideoStatus.PENDING_APPROVAL.value]
    }

    template = loader.get_template('video_list.html')

    return HttpResponse(template.render({
      'videos': result,
      'gloss_id': gloss_id
    }, request))


class GlossesDownloadView(View):
  def get(self, request, gloss_id=None):
      videos = Video.objects.select_related('gloss').select_related('user').filter(~Q(user_id=config.SAMPLE_VIDEO_USER_ID), status__gte=VideoStatus.REJECTED)
      if gloss_id:
        videos = videos.filter(gloss_id=gloss_id)
      commands = []
      prefix = ''
      for video in videos:
        if not prefix and gloss_id:
          prefix = video.gloss.text + '-'
        command = 'wget -O {gt}-{username}-{status}-{time}.mp4 {base_url}{video_path}'.format(
            gt=video.gloss.text,
            username=video.user.username,
            time=datetime.utcfromtimestamp(video.created_time).strftime('%Y%m%d%H%M%S'),
            base_url='' if str(video.video_path)[:4] == 'http' else request.get_host(),
            status=VideoStatus(video.status).name,
            video_path=video.video_path
          )
        commands.append(command)
      response = HttpResponse('\n'.join(commands), content_type='application/x-sh')
      response['Content-Disposition'] = 'attachment; filename="{}batch-download.sh"'.format(prefix)
      return response
