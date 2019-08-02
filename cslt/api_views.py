import time

from django.http import HttpResponse
from rest_framework import views
from rest_framework.response import Response
from django.db.models import Q, Sum, Count
from rest_framework.parsers import MultiPartParser, FormParser
from django.utils.translation import ugettext_lazy as _
from prometheus_client import start_http_server, generate_latest, Counter, Gauge, Histogram

from cslt import services, config
from cslt.models import Category, Video, Score, VideoStatus, Gloss, ScoreType, \
  GlossType, ScoreValue
from cslt.serializers import *
from rest_framework_simplejwt.views import TokenError, TokenViewBase
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, \
  TokenRefreshSerializer

from cslt.services import update_video_and_gloss_by_review
from cslt.services import update_video_and_gloss_by_new_upload

from cslt.utils import Convert


logger = logging.getLogger(__name__)

COMMON_URL_ERROR = {'code': 404, 'message': _('Not Found')}

# A counter to count the total number of HTTP requests
METRIC_REQUESTS = Counter('http_requests_total', 'Total HTTP Requests (count)',
                          ['method', 'endpoint'])

# A gauge (i.e. goes up and down) to monitor the total number of in progress requests
METRIC_IN_PROGRESS = Gauge('http_requests_inprogress', 'Number of in progress HTTP requests')

# A histogram to measure the latency of the HTTP requests
METRIC_TIMINGS = Histogram('http_request_duration_seconds', 'HTTP request latency (seconds)')

UPLOAD_FORBIDDENED_VIDEO_STATUS = [
    VideoStatus.SAMPLE, VideoStatus.APPROVED,
    VideoStatus.DELETED, VideoStatus.FORBIDDEN]


def build_resp(data=None, code=0, message=None):
  resp = {'code': code}
  if message:
    resp['message'] = message
  if data:
    resp['data'] = data

  return resp


# <editor-fold desc="token">
class TokenView(TokenViewBase):
  serializer_class = None

  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def post(self, request, *args, **kwargs):
    METRIC_REQUESTS.labels(method='POST', endpoint='api/auth/').inc()

    serializer = self.get_serializer(data=request.data)

    try:
      serializer.is_valid(raise_exception=True)
      logger.info('user %s login at %d' % (request.data['username'], time.time()))
      resp = build_resp(serializer.validated_data)
    except TokenError as e:
      resp = build_resp(code=401, message=_(e.args[0]))

    return Response(resp)


class TokenObtainView(TokenView):
  """
  Takes a set of user credentials and returns an access and refresh JSON web
  token pair to prove the authentication of those credentials.
  """
  serializer_class = TokenObtainPairSerializer


class TokenRefreshView(TokenView):
  """
  Takes a refresh type JSON web token and returns an access type JSON web
  token if the refresh token is valid.
  """
  serializer_class = TokenRefreshSerializer
# </editor-fold>


# <editor-fold desc="account">
class ChangePasswordView(views.APIView):
  """
  An endpoint for changing password.
  """
  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def put(self, request):
    METRIC_REQUESTS.labels(method='GET', endpoint='api/account/password').inc()

    user = self.request.user
    serializer = ChangePasswordSerializer(data=request.data)

    if serializer.is_valid():
        # Check old password
        old_password = serializer.data.get("old_password")
        if not user.check_password(old_password):
          resp = build_resp(
            code=50103,
            message=_('Wrong old password'))
          return Response(resp)
        # set_password also hashes the password that the user will get
        user.set_password(serializer.data.get("new_password"))
        user.save()
        return Response(build_resp(code=0))

    return Response(build_resp(code=500, message=_('Error occurred')))


class AuthMediaView(views.APIView):
  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def get(self, request, path):
    METRIC_REQUESTS.labels(method='GET', endpoint='api/media/').inc()

    response = HttpResponse()
    response["Content-Disposition"] = "attachment; filename={0}".format(
        path.split('/')[-1])
    response['X-Accel-Redirect'] = "/media/{0}".format(path)
    return response


class AgreementView(views.APIView):
  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def post(self, request):
    METRIC_REQUESTS.labels(method='POST', endpoint='api/account/agreement').inc()
    logger.info('user [%s] has agree with the agreements' % request.user.username)
    resp = {
      'code': 0
    }

    return Response(resp)

  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def get(self, request):
    METRIC_REQUESTS.labels(method='GET', endpoint='api/account/agreement').inc()

    return Response({
      'code': 0,
      'data': '/static/agreements/' + request.user.username + '-agreement.pdf'
    })
# </editor-fold>


# <editor-fold desc="category">
class CategoryView(views.APIView):
  """
  Get categories or single category information.

  list:
  return root categories list.
  Example:
    /api/categories

  get:
  Get one category details.
  Example:
    /api/categories/1
  """

  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def get(self, request, id=None):
    METRIC_REQUESTS.labels(method='GET', endpoint='api/categories/').inc()

    if not id:
      categories = Category.objects.filter(parent_id=0).order_by('seq')
      serializer = CategorySerializer(categories, many=True)
    else:
      try:
        id = int(id)
      except ValueError:
        return Response(build_resp(COMMON_URL_ERROR))

      categories = Category.objects.get(id=id)
      serializer = CategorySerializer(categories)

    resp = {
      'code': 0,
      'data': serializer.data
    }

    return Response(resp)
# </editor-fold>


class DictionaryView(views.APIView):
  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def get(self, request):
    METRIC_REQUESTS.labels(method='GET', endpoint='api/dictionary/').inc()
    glosses = Gloss.objects.filter(gloss_type=GlossType.SINGLE_WORD)

    qs = request.GET

    if 'q' in qs:
      query = qs['q']
      glosses = glosses.filter(text__istartswith=query)

    glosses = glosses.order_by(Convert('text', 'gbk').asc())

    try:
      offset = int(qs['offset']) if 'offset' in qs else 0
      limit = int(qs['limit']) if 'limit' in qs else settings.PAGE_SIZE
    except TypeError:
      offset = 0
      limit = settings.PAGE_SIZE

    total = glosses.count()
    glosses = glosses.all()[offset: offset + limit]

    serializer = GlossSerializer(glosses, many=True)
    resp = {
      'code': 0,
      'data': {
        'total': total,
        'next': offset + limit,
        'data': serializer.data if len(glosses) > 0 else []
      }
    }

    return Response(resp)


class GlossView(views.APIView):
  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def get(self, request, order=None):
    METRIC_REQUESTS.labels(method='GET', endpoint='api/glosses/').inc()
    glosses = Gloss.objects

    qs = request.GET

    if 'q' in qs:
      query = qs['q']
      glosses = glosses.filter(text__icontains=query).order_by('text')
    elif order == 'latest':
      glosses = glosses.order_by('-created_time')
    elif order == 'recommend':
      glosses = glosses.order_by('video_count')
    else:
      glosses = glosses.order_by('text')

    try:
      offset = int(qs['offset']) if 'offset' in qs else 0
      limit = int(qs['limit']) if 'limit' in qs else settings.PAGE_SIZE
    except TypeError:
      offset = 0
      limit = settings.PAGE_SIZE

    total = glosses.count()
    glosses = glosses.all()[offset: offset + limit]

    serializer = GlossSerializer(glosses, many=True)
    resp = {
      'code': 0,
      'data': {
        'total': total,
        'next': offset + limit,
        'data': serializer.data if len(glosses) > 0 else []
      }
    }

    return Response(resp)


# <editor-fold desc="video">
class VideoView(views.APIView):
  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def get(self, request, id=None):
    """
    Get videos or single video information.

    list:

    return paged video entries with filters of request get params.
      filters:
        * author ( user id, special value: self,
                   if null the api will return a list without self video. )
        * query ( any text in gloss label )
        * categories ( comma separated numbers, categories id )
        * offset ( the result offset to start shown )
        * limit ( the list maximum length )

    Example:
      /api/videos
      /api/videos?author=self
      /api/videos?author=1&limit=10

    get:

    Get one video details. The id field is a uuid, each video has a uuid field
    to identify the video.

    Example:
      /api/videos/c212f20c-5734-4e27-880c-e5469164dd7d

    Args:
      request:
      id:

    Returns:

    """
    METRIC_REQUESTS.labels(method='GET', endpoint='api/videos/').inc()
    if id and id not in ['self', 'unreviewed']:
      try:
        video = Video.objects.get(uuid=id)
      except Video.DoesNotExist:
        return Response(build_resp(COMMON_URL_ERROR))

      serializer = VideoSerializer(video)
      return Response(build_resp(serializer.data))

    status = [VideoStatus.PENDING_APPROVAL,
              VideoStatus.APPROVED,
              VideoStatus.REJECTED]
    qs = dict(request.query_params)
    if not qs:
      qs = {}
    if id == 'self':
      qs['author'] = 'self'

    if id == 'unreviewed':
      qs['unreviewed'] = True
      status = VideoStatus.PENDING_APPROVAL

    if 'status' in qs:
      try:
        status = VideoStatus[qs['status'][0].upper()]
      except (KeyError, IndexError):
        pass

    data, next_offset, total = services.get_videos(request.user, qs, status)
    video_serializer = VideoSerializer(data, many=True)
    result = video_serializer.data if len(data) > 0 else []
    for item in result:
      item['status'] = VideoStatus(item['status']).name
    data = {
      'total': total,
      'next': next_offset,
      'data': result
    }

    resp = build_resp(data)

    return Response(resp)

  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def post(self, request):
    """
    Create new video entry.

    post:
      {
        "gloss_id": number|number list
      }
      return video uuid|uuid list (named "upload_key"), you can use this uuid to
      get video info, or upload video.
    Args:
      request:

    Returns:

    """
    METRIC_REQUESTS.labels(method='POST', endpoint='api/videos/').inc()
    try:
      if type(request.data['gloss_id']) == int:
        glosses = [request.data['gloss_id']]
      else:
        glosses = request.data['gloss_id']
    except KeyError:
      return Response(build_resp(code=6701, message=_('Parameters error')))

    if not isinstance(glosses, list):
      return Response(build_resp(code=6701, message=_('Parameters error')))

    uuids = services.create_videos(request.user, glosses)

    resp = build_resp({'upload_key': uuids})
    return Response(resp)


class UploadView(views.APIView):
  parser_classes = (MultiPartParser, FormParser)

  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def post(self, request, id):
    """
    Upload video file server.

    This api needs multipart/form-data form post, the file field is named 'file'.
    The upload file type only supports 'video/mp4'.

    Examples:
      /api/videos/b2121b40-7c21-486f-b8a5-8dd91f5b80a8/upload
      Content-Disposition: form-data; name="video"; filename="video.mp4"
      Content-Type: video/mp4
      Content-Disposition: form-data; name="thumbnail"; filename="thumbnail.png"
      Content-Type: image/png
    """
    METRIC_REQUESTS.labels(method='POST', endpoint='api/videos/<slug:id>/upload').inc()
    try:
      video = Video.objects.get(uuid=id)
    except Video.DoesNotExist:
      return Response(build_resp(COMMON_URL_ERROR))

    user_id = request.user.id
    if video.user_id != user_id:
      resp = build_resp(
          code=50070, message=_('No permission to upload this video'))
      return Response(resp)

    if video.status in UPLOAD_FORBIDDENED_VIDEO_STATUS:
      resp = build_resp(
          code=50071,
          message=_('Invalid upload, The video has been forbidden/deleted'))
      return Response(resp)

    request.data['user_id'] = user_id
    request.data['uuid'] = id
    vs = VideoUploadSerializer(data=request.data)

    if vs.is_valid():
      try:
        vs.save()
      except Exception as e:
        resp = build_resp(code=400, message=e.args[0])
        return Response(resp)

      update_video_and_gloss_by_new_upload(video, vs.validated_data['video'],
                                           vs.validated_data['thumbnail'])

      score = Score(user_id=request.user.id,
                    video_id=video.id,
                    video_owner_id=request.user.id,
                    score_type=ScoreType.CREATE_VIDEO,
                    value=ScoreValue.CREATE_VIDEO,
                    created_time=int(time.time()))
      score.save()

      resp = build_resp(vs.validated_data)
      return Response(resp)
    else:
      resp = build_resp(code=500, message=_('Error occurred'))
      return Response(resp)
# </editor-fold>


class ScoreView(views.APIView):
  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def get(self, request):
    METRIC_REQUESTS.labels(method='GET', endpoint='api/review/').inc()
    score_values = [{
      'label': 'review video', 'value': 1
    }, {
      'label': 'create video', 'value': 2
    }, {
      'label': 'create gloss', 'value': 1
    }, {
      'label': 'review approved', 'value': 3
    }, {
      'label': 'review rejected', 'value': 0
    }, {
      'label': 'sample', 'value': 4
    }]
    return Response(build_resp(score_values))

  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def post(self, request, uuid, action=None):
    METRIC_REQUESTS.labels(method='POST', endpoint='api/review/').inc()
    try:
      video = Video.objects.get(uuid=uuid)
    except Video.DoesNotExist:
      return Response(build_resp(COMMON_URL_ERROR))

    if video.user.id == request.user.id:
      resp = build_resp(code=50061, message=_('User cannot review self video'))
      return Response(resp)

    if Gloss.objects.filter(sample_video_id=video.id).exists():
      resp = build_resp(code=50062, message=_('Forbid voting a sample video'))
      return Response(resp)

    # reviewer score
    try:
      score = Score.objects.get(user_id=request.user.id, video_id=video.id,
                                score_type=1)
    except Score.DoesNotExist:
      score = Score(user_id=request.user.id,
                    video_id=video.id,
                    video_owner_id=video.user.id,
                    score_type=ScoreType.REVIEW_VIDEO,
                    value=ScoreValue.REVIEW_VIDEO,
                    created_time=int(time.time()))
    score.save()

    action = VideoStatus.APPROVED if action == 'approve' else VideoStatus.REJECTED
    update_video_and_gloss_by_review(video, action)

    # owner's video quality score
    try:
      score = Score.objects.get(user_id=request.user.id, video_id=video.id,
                                score_type=ScoreType.VIDEO_QUALITY)
    except Score.DoesNotExist:
      score = Score(user_id=request.user.id,
                    video_id=video.id,
                    video_owner_id=video.user.id,
                    score_type=ScoreType.VIDEO_QUALITY,
                    value=ScoreValue.APPROVE_VIDEO if action == 'approved' else ScoreValue.REJECT_VIDEO,
                    created_time=int(time.time()))
    score.save()

    video_score = services.get_video_score(video.id)

    user_scores = services.get_user_scores(request.user.id)
    data = {
      'uuid': uuid,
      'value': 1,
      'video_score': video_score,
      'user_scores': user_scores
    }
    return Response(build_resp(data))


class ProfileView(views.APIView):

  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def get(self, request):
    METRIC_REQUESTS.labels(method='GET', endpoint='api/profile/').inc()
    data = {
      'id': request.user.id,
      'username': request.user.username,
      'settings': {},
      'scores': services.get_user_scores(request.user.id)
    }
    return Response(build_resp(data))


class BunchView(views.APIView):
  """
  BunchView provides recording tasks to users.

   Note that there are two types of users, and their recording tasks
    are distributed differently:
   - Reference video recording user: Can record glosses that has no reference video only,
     and can record without limit continuously
   - Training video recording user: Can only record glosses when their pending_approval
     videos are below a limit. This is to ensure training videos are timely verified
     before next recording tasks. We intend to keep the recording-review-correction loop
     small in quantity and time.
  """
  def _getUserPendingApprovalVideoCount(self, user):
    qs = {'author': 'self', 'offset': [0], 'limit': [10000]}
    data, next_offset, total = services.get_videos(user, qs, status=VideoStatus.PENDING_APPROVAL)
    return 0 if data == None else total

  def _isReferenceCreator(self, user_id):
    return user_id == config.SAMPLE_VIDEO_USER_ID

  def _getReferenceVideoBunch(self, user_id):
    sql = '''SELECT g.* FROM cslt.cslt_gloss g
        WHERE g.gloss_type <> 0 AND g.id NOT IN (
          SELECT v.gloss_id FROM cslt.cslt_video v
          WHERE v.user_id = %d) ORDER BY g.id;''' % (user_id)
    glosses = list(Gloss.objects.raw(sql))
    return glosses

  def _getTrainingVideoBunch(self, request_user):
    # Check requested user's pending_approval video count. Do not assign more
    # recording tasks if the pending_approval videos exceeds a limit.
    user_pending_video_count = self._getUserPendingApprovalVideoCount(request_user)
    limit = settings.PENDING_APPROVAL_VIDEO_LIMIT_PER_USER - user_pending_video_count
    if limit < 1:
      raise ValueError('Too many pending approval videos')

    sql = '''SELECT g.* FROM cslt.cslt_gloss g
        LEFT JOIN (
          SELECT g.*, COUNT(v.id) AS count
            FROM cslt.cslt_gloss g
            JOIN cslt.cslt_video v ON v.gloss_id = g.id
            WHERE v.user_id = %d AND v.status > 0
            GROUP BY g.id) g2
        ON g2.id = g.id WHERE g.gloss_type > 0 AND (
           g.approved_video_count is NULL or g.approved_video_count < %d)
        ORDER BY g.id
        LIMIT %d;''' % (request_user.id, settings.DEFAULT_TARGET_TRAINING_VIDEO_COUNT_PER_GLOSS, limit)

    glosses = list(Gloss.objects.raw(sql))

    glosses_map = {k.id: k for v, k in enumerate(glosses)}

    gloss_ids = Video.objects.filter(gloss_id__in=[gloss.id for gloss in glosses], user_id=request_user.id).values('gloss_id').annotate(video_count=Count('gloss_id'))

    for item in gloss_ids:
      if item['video_count'] > config.ONE_GLOSS_RECORDING_LIMIT:
        glosses_map.pop(item['gloss_id'])

    if gloss_ids:
      glosses = glosses_map.values()

    # Insert reference video place holder if it does not exist.
    for gloss in glosses:
      if not gloss.sample_video.thumbnail:
        gloss.sample_video.thumbnail = config.NO_PIC_URL

    return glosses

  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def get(self, request):
    METRIC_REQUESTS.labels(method='GET', endpoint='api/bunch/').inc()
    user_id = request.user.id

    if self._isReferenceCreator(user_id):
      glosses = self._getReferenceVideoBunch(user_id)
    else:
      try:
        glosses = self._getTrainingVideoBunch(request.user)
      except ValueError:
        return Response(build_resp(None, 406, _('Too many pending approval videos')))

    gs = GlossSerializer(glosses, many=True)
    return Response(build_resp(gs.data))


class StatisticView(views.APIView):

  @METRIC_TIMINGS.time()
  @METRIC_IN_PROGRESS.track_inprogress()
  def get(self, request):
    METRIC_REQUESTS.labels(method='GET', endpoint='api/profile/statics').inc()
    score = Score.objects.get(pk=1)
    score.value += 1
    score.save()
