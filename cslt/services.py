import time
import uuid

from django.db.models import Q, Sum, Count

from cslt import settings, config
from cslt.models import Video, VideoStatus, ScoreType, Score, Gloss

INITIAL_SUMMARY = {'approved': 0, 'rejected': 0}


def create_videos(user, gloss_ids):
  """
  Create videos following gloss ids

  :param user: owner
  :param gloss_ids: a list of gloss ids
  :return: created videos uuids list or one uuid for single gloss.
  """
  uuids = []
  for gloss_id in gloss_ids:
    video = Video(
        user_id=user.id,
        gloss_id=gloss_id,
        uuid=str(uuid.uuid4()),
        review_summary=INITIAL_SUMMARY,
        created_time=int(time.time()),
        status=VideoStatus.WAITING_UPLOAD
    )
    video.save()
    uuids.append(video.uuid)

  if len(uuids) == 1:
    uuids = uuids[0]

  return uuids


def update_video_and_gloss_by_new_upload(video, video_path, thumbnail_path):
  """Save a newly uploaded video and update its gloss data accordingly."""
  video.video_path = video_path
  video.thumbnail = thumbnail_path

  if video.user_id == config.SAMPLE_VIDEO_USER_ID:
    video.gloss.sample_video_id = video.id
    video.status = VideoStatus.SAMPLE
  else:
    video.review_summary = INITIAL_SUMMARY
    video.status = VideoStatus.PENDING_APPROVAL
    video.gloss.pending_approval_video_count += 1

  # hack for sample recording yinhuan
  if user_id == 36:
    video.status = VideoStatus.APPROVED
    video.gloss.pending_approval_video_count -= 1
    video.gloss.approved_video_count += 1

  video.gloss.save()
  video.save()


def update_video_and_gloss_by_review(video, action):
  if action == VideoStatus.REJECTED:
    video.review_summary['rejected'] += 1
  elif action == VideoStatus.APPROVED:
    video.review_summary['approved'] += 1
  else:
    raise ValueError("Unknown video review action of " + action)

  if video.status == VideoStatus.PENDING_APPROVAL.value:
    if video.review_summary['rejected'] >= settings.MIN_REJECTION_COUNT_TO_REJECTED_STATUS:
      video.status = VideoStatus.REJECTED
      video.gloss.rejected_video_count += 1
      video.gloss.pending_approval_video_count -= 1
      video.gloss.save()
    elif video.review_summary['approved'] >= settings.MIN_APPROVAL_COUNT_TO_APPROVAL_STATUS:
      video.status = VideoStatus.APPROVED
      video.gloss.approved_video_count += 1
      video.gloss.pending_approval_video_count -= 1
      video.gloss.save()
  video.save()


def get_videos(user, qs, status=VideoStatus.APPROVED):
  try:
    offset = int(qs['offset'][0]) if 'offset' in qs else 0
    limit = int(qs['limit'][0]) if 'limit' in qs else settings.PAGE_SIZE
  except TypeError:
    offset = 0
    limit = 10000
  else:
    try:
      offset = int(qs['offset']) if 'offset' in qs else 0
      limit = int(qs['limit']) if 'limit' in qs else settings.PAGE_SIZE
    except TypeError:
      offset = 0
      limit = settings.PAGE_SIZE

  categories = qs['cid'].split(',') if 'cid' in qs else []
  query = qs['q'] if 'q' in qs else ''

  if type(status) == list:
    videos = Video.objects.filter(status__in=status)
  else:
    videos = Video.objects.filter(status=status)

  author = 0
  if 'author' in qs:
    try:
      author = user.id if qs['author'] == 'self' else int(qs['author'])
    except TypeError:
      pass

  if author:
    videos = videos.filter(user_id=author)
    if author == user.id:
      videos = videos.order_by('-created_time')
  else:
    videos = videos.filter(~Q(user_id=user.id))

  unreviewed = 'unreviewed' in qs
  if unreviewed:
    videos = videos.filter(~Q(score__user__id=user.id,
                              score__score_type=ScoreType.REVIEW_VIDEO))

  if len(categories) > 0:
    videos = videos.filter(category_id__in=categories)

  if query != '':
    videos = videos.filter(gloss_text__contains=query)

  videos = videos.exclude(gloss__gloss_type=0)

  total = videos.count()
  next_offset = offset + limit if offset + limit < total else 0
  data = videos[offset: offset + limit]
  return data, next_offset, total


def get_video_score(video_id):
  try:
    video_score = Score.objects.filter(
        video_id=video_id, score_type=ScoreType.VIDEO_QUALITY).annotate(
        total=Sum('value'))[0].total
  except (Score.DoesNotExist, IndexError):
    video_score = 0

  return video_score


def get_user_scores(user_id):
  scores = {str(key) + '_score': 0 for key in ScoreType}
  counts = {str(key) + '_count': 0 for key in ScoreType}
  try:
    user_score_model = Score.objects.values(
      'score_type').exclude(video__gloss__gloss_type=0).filter(
        (Q(user_id=user_id) &
        ~Q(score_type=ScoreType.VIDEO_QUALITY)) |
        (Q(video_owner_id=user_id) &
        Q(score_type=ScoreType.VIDEO_QUALITY))).annotate(
        total=Sum('value'), count=Count('value'))
  except Score.DoesNotExist:
    user_score_model = {}

  if user_score_model:
    for s in user_score_model:
      scores[str(ScoreType(s['score_type'])) + '_score'] = s['total']
      counts[str(ScoreType(s['score_type'])) + '_count'] = s['count']
  return {**counts, **scores}
