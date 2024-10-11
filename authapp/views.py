from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.views.generic import View
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.sites.shortcuts import get_current_site
from django.urls import NoReverseMatch,reverse
from django.utils.http import urlsafe_base64_decode,urlsafe_base64_encode
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes,DjangoUnicodeDecodeError,force_str
#emails-------------------
from django.conf import settings
from django.core.mail import EmailMessage  
from django.core.mail import send_mail,EmailMultiAlternatives
# getting token from utils.py
from .utils import generate_token
#for reset password
from django.contrib.auth.tokens import PasswordResetTokenGenerator


#Threading 
import threading
class EmailThread(threading.Thread):
    def __init__(self,email_message):
        self.email_message=email_message
        threading.Thread.__init__(self)
    def run(self):
       self.email_message.send()
    
# Create your views here.
def handellogout(request): 
    logout(request)
    messages.info(request,"Logout Successfully")
    return redirect('/auth/login/')  # You should add a redirect after logout

def handellogin(request):
    if request.method == 'POST':
        get_email = request.POST.get('email')
        get_password = request.POST.get('pass1') 
        myuser = authenticate(username=get_email, password=get_password) 
        if myuser is not None:
            login(request, myuser)
            messages.success(request, "Login successful")
            return redirect('/')
        else:
            messages.error(request, 'Invalid Credentials')
            return redirect('/auth/login/')  
        
    return render(request, "authentication/login.html")

def signup(request):
    if request.method == 'POST':
        get_email = request.POST.get('email')
        get_password = request.POST.get('pass1')
        get_confirm_password = request.POST.get('pass2')
        
        if get_password != get_confirm_password:
            messages.warning(request, 'Passwords do not match')
            return redirect('/auth/signup/')
        
        try:
            if User.objects.get(username=get_email):
                messages.warning(request, 'Email is already taken')
                return redirect('/auth/signup/')
        except User.DoesNotExist:
            pass 
        
        myuser = User.objects.create_user(get_email, get_email, get_password)
        myuser.is_active = False
        myuser.save()
        #--------------------------------------------------------------------
        current_site=get_current_site(request)
        get_email_subject="Activate your Account"
        message=render_to_string('authentication/activate.html',{
          'user':myuser,
          'domain':'127.0.0.1:8000',
          'uid':force_str(urlsafe_base64_encode(force_bytes(myuser.pk))),
          'token':generate_token.make_token(myuser)
            
        })
        email_message = EmailMessage(get_email_subject, message,settings.EMAIL_HOST_USER, [get_email])
        EmailThread(email_message).start()
        # email_message.send()
        messages.success(request, 'Activate your account by clicking the link sent to your email.')
        return redirect('/auth/login/') 
    
    return render(request, "authentication/signup.html")


class ActivateAccountView(View):
    def get(self, request, uidb64, token):
        try:
            uid = force_str(urlsafe_base64_decode(uidb64))
            myuser = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            myuser = None
        
        if myuser is not None and generate_token.check_token(myuser, token):
            myuser.is_active = True
            myuser.save()
            messages.success(request, 'Account activated successfully')
            return redirect('/auth/login/')
        else:
            return render(request, 'authentication/activatefail.html')
class RequestResetEmailView(View):
    def get(self,request):
        return render(request,'authentication/request-reset-email.html')
    
    def post(self,request):
        email=request.POST['email']
        user=User.objects.filter(email=email)

        if user.exists():
            current_site=get_current_site(request)
            email_subject='[Reset Your Password]'
            message=render_to_string('authentication/reset-user-password.html',{
                'domain':'127.0.0.1:8000',
                'uid':urlsafe_base64_encode(force_bytes(user[0].pk)),
                'token':PasswordResetTokenGenerator().make_token(user[0])
            })
#-------------------------------------------------
            email_message=EmailMessage(email_subject,message,settings.EMAIL_HOST_USER,[email])
            email_message.send()
            EmailThread(email_message).start()

            messages.info(request,f"WE HAVE SENT YOU AN EMAIL WITH INSTRUCTIONS ON HOW TO RESET THE PASSWORD {message} " )
            return render(request,'authentication/request-reset-email.html')

class SetNewPasswordView(View):
    def get(self,request,uidb64,token):
        context = {
            'uidb64':uidb64,
            'token':token
        }
        try:
            user_id=force_bytes(urlsafe_base64_decode(uidb64))
            user=User.objects.get(pk=user_id)

            if  not PasswordResetTokenGenerator().check_token(user,token):
                messages.warning(request,"Password Reset Link is Invalid")
                return render(request,'authentication/request-reset-email.html')

        except DjangoUnicodeDecodeError as identifier:
            pass

        return render(request,'authentication/set-new-password.html',context)

    def post(self,request,uidb64,token):
        context={
            'uidb64':uidb64,
            'token':token
        }
        get_password=request.POST['pass1']
        get_confirm_password=request.POST['pass2']
        if get_password!=get_confirm_password:
            messages.warning(request,"Password is Not Matching")
            return render(request,'authentication/set-new-password.html',context)
        
        try:
            user_id=force_bytes(urlsafe_base64_decode(uidb64))
            user=User.objects.get(pk=user_id)
            user.set_password(get_password)
            user.save()
            messages.success(request,"Password Reset Success Please Login with NewPassword")
            return redirect('/auth/login/')

        except DjangoUnicodeDecodeError as identifier:
            messages.error(request,"Something Went Wrong")
            return render(request,'authentication/set-new-password.html',context)