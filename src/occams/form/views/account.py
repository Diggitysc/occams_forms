from pyramid.httpexceptions import HTTPFound, HTTPForbidden
from pyramid.security import forget
from pyramid.view import view_config, forbidden_view_config
from wtforms import Form, StringField, validators, PasswordField
from wtforms.widgets.html5 import EmailInput

from .. import _, Session, models


class LoginForm(Form):

    login = StringField(
        label=_(u'Email address'),
        widget=EmailInput(),
        validators=[
            validators.Required(),
            validators.Length(max=32),
            validators.Email(),
        ])

    password = PasswordField(
        label=_(u'Password'),
        validators=[
            validators.Required(),
            validators.Length(min=5, max=32)
        ])


@view_config(
    route_name='account_login',
    renderer='occams.form:templates/account/login.pt')
@forbidden_view_config(
    renderer='occams.form:templates/account/login.pt')
def login(request):

    if (request.matched_route.name != 'account_login'
            and request.authenticated_userid):
        # If an authenticated user has reached this controller without
        # intentionally going to the login view, assume permissions
        # error
        return HTTPForbidden()

    # Figure out where the user came from so we can redirect afterwards
    referrer = request.GET.get('referrer', request.current_route_path())

    if not referrer or referrer == request.route_path('account_login'):
        # Never use the login as the referrer
        referrer = request.route_path('home')

    form = LoginForm(request.POST)

    # Only process the input if the user intented to post to this view
    # (could be not-logged-in redirect)
    if (request.method == 'POST'
            and request.matched_route.name == 'account_login'
            and form.validate()):
        # XXX: Hack for this to work on systems that have not set the
        # environ yet. Pyramid doesn't give us access to the policy
        # publicly, put it's still available throught this private
        # variable and it's usefule in leveraging repoze.who's
        # login mechanisms...
        who_api = request._get_authentication_policy()._getAPI(request)

        authenticated, headers = who_api.login({
            'login': form.login.data,
            'password': form.password.data})
        if not authenticated:
            request.session.flash(_(u'Invalid credentials'), 'error')
        else:
            user = (
                Session.query(models.User)
                .filter_by(key=form.login.data)
                .first())
            if not user:
                Session.add(models.User(key=request.login.data))
            return HTTPFound(location=referrer, headers=headers)

    # forcefully forget any credentials
    request.response_headerlist = forget(request)

    return {
        'form': form,
        'referrer': referrer
    }


@view_config(route_name='account_logout')
def logout(request):
    who_api = request._get_authentication_policy()._getAPI(request)
    headers = who_api.logout()
    return HTTPFound(location=request.route_path('home'), headers=headers)
