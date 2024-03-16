from flask import Blueprint, render_template, request, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from . import db
from .models import History, Farm
import pytz
from datetime import datetime

from werkzeug.security import generate_password_hash
from PIL import Image
import base64
import cv2
from werkzeug.utils import secure_filename
import requests
import re
from io import BytesIO
from sqlalchemy import func, and_


from ultralytics import YOLO


views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    selected_city = request.form.get('selected_city')
    farm = Farm.query.filter_by(user_id=current_user.id)\
                    .group_by(Farm.city)\
                    .order_by(func.count().desc())\
                    .all()
    if selected_city:
        city = selected_city
    elif farm:
        city = farm[0].city
    else:
        city = False
    if city:           
        url='http://api.openweathermap.org/data/2.5/forecast?q={},MY&units=imperial&appid=ad6d08a17fed0babecf83669a0ce765f'
        r = requests.get(url.format(city)).json()
        # print("r: ",r)
        if 'list' not in r:
            return {'error': 'An error occurred while fetching the weather forecast'}

        forecasts = r['list']
        unique_forecast_days = []
        five_days_forecast = []
        temp=[]
        wind=[]
        humi=[]
        date=[]
        icon=[]
        desc=[]
        for forecast in forecasts:
            forecast_date = forecast['dt_txt'].split(" ")[0]
            if forecast_date not in unique_forecast_days:
                unique_forecast_days.append(forecast_date)
                five_days_forecast.append(forecast)
        for item in five_days_forecast:
            temp.append(round((item['main']['temp'] - 32)*5/9, 2))
            wind.append(item['wind']['speed'])
            humi.append(item['main']['humidity'])
            date.append(item['dt_txt'].split(" ")[0])
            icon.append(item['weather'][0]['icon'])
            desc.append(item['weather'][0]['description'])
            
        return render_template("home.html", user=current_user, city=city, temp=temp, wind=wind, humi=humi, date=date, icon=icon, desc=desc, farm=farm)
    return render_template("home.html", user=current_user,city="false")


@views.route('/detection', methods=['GET', 'POST'])
@login_required
def detection():
    if request.method == 'POST': 
        try:
            data = get_location()
            print("location: ",data)
            if 'pic' in request.files:
                upload_img = request.files['pic']
                
                img = Image.open(upload_img)
                
                yolo = YOLO('best.pt')
                results = yolo.predict(img, max_det=1)
                process_img = results[0].plot()

                _, img_bytes = cv2.imencode('.jpg', process_img)
                filename = secure_filename(upload_img.filename)

                clss = results[0].boxes.cls.cpu().tolist()
                names = results[0].names                                   
                confs = results[0].boxes.conf.float().cpu().tolist()
                
                result = "No diseases detected / The model currently do not support the plants or disease" 
                conf="" 
                control_strategies=""
                disease_description=""
                                
                for cls, conf in zip(clss, confs):
                    if names[cls]:
                        result = names[cls]
                        conf=conf
                
                final_img = History(img=img_bytes.tobytes(), mimetype=upload_img.mimetype, name=filename, user_id=current_user.id, label=result, conf=conf, date=datetime.now(pytz.timezone('Asia/Singapore')).replace(microsecond=0))
                db.session.add(final_img)
                db.session.commit()
                
                encoded_image = base64.b64encode(img_bytes.tobytes()).decode('utf-8')
                
                disease_info = {
                    "Apple Scab": {
                        "description": "Apple scab is a fungal disease characterized by olive-green to black lesions on leaves, fruit, and twigs. It leads to defoliation, reduced fruit quality, and can severely impact apple orchards.",
                        "control_strategies": "Use resistant apple varieties, apply fungicides before symptoms appear, practice proper sanitation by removing infected leaves, and maintain good air circulation within the orchard."
                    },
                    "Apple Black Rod": {
                        "description": "Apple black rot, caused by the fungus Botryosphaeria obtusa, results in brown, circular lesions on fruit with concentric rings. Infected apples become mummified, posing a threat to the entire orchard.",
                        "control_strategies": "Apply fungicides during the growing season, prune infected branches, remove mummified fruit, and practice proper orchard sanitation."
                    },
                    "Cedar Apple Rust": {
                        "description": "Cedar apple rust affects apples and cedars, displaying bright orange spore-producing structures on leaves and fruit. It can cause defoliation and impact fruit quality.",
                        "control_strategies": "Remove nearby cedar hosts, use resistant apple varieties, apply fungicides during the spring, and practice proper orchard sanitation."
                    },
                    "Cherry Powdery Mildew": {
                        "description": "Cherry powdery mildew is identified by powdery white patches on leaves. Severe infections lead to distorted leaves and unmarketable fruit.",
                        "control_strategies": "Apply fungicides preventively, manage irrigation practices, prune for good air circulation, and remove infected plant parts promptly."
                    },
                    "Grape Black Rot": {
                        "description": "Grape black rot, caused by the fungus Guignardia bidwellii, results in circular lesions on leaves and fruit. Infected grapes shrivel into mummies, causing significant crop losses.",
                        "control_strategies": "Apply fungicides early in the growing season, practice proper sanitation by removing mummies, and choose resistant grape varieties."
                    },
                    "Grape Esca": {
                        "description": "Grapevine measles or esca is characterized by cryptic symptoms, including superficial spots on fruit and a 'tiger stripe' pattern on leaves. Severe cases lead to vine decline and \"apoplexy,\" causing rapid vine death.",
                        "control_strategies": "Currently, there are no effective management strategies. Research focuses on protecting pruning wounds to minimize fungal infections."
                    },
                    "Grape Leaf Blight": {
                        "description": "Grape leaf blight is characterized by linear reddish-brown streaks on shoots, leading to wilting and drying of affected shoots. Cankers may develop, impacting grapevine health.",
                        "control_strategies": "Use high-health plant material, monitor for unusual symptoms, and practice on-farm biosecurity and hygiene to prevent the spread of the bacterium Xylophilus ampelinus."
                    }
                }
                
                if "Healthy" in result:
                    disease_description = "The plant appears to be healthy with no detected diseases."
                    control_strategies = "Continue regular plant care practices to maintain plant health."
                elif result in disease_info:
                    disease_description = disease_info[result]["description"]
                    control_strategies = disease_info[result]["control_strategies"]
                
                flash('Upload image successfully!', category='success')                
                return render_template('detection.html', image=encoded_image, user=current_user, predict=True, result=result, treatment=control_strategies, desc=disease_description,location=data)
                
        except OSError:
            flash('Please upload an image!', category='error')
            
    return render_template("detection.html", user=current_user)

@views.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST': 
        phone = request.form.get('phone')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')
        
        phone_regex = "^(01\\d{1}-\\d{7}|01\\d{1}-\\d{8}|01\\d{8}|01\\d{9})$"
        phone_pattern = re.compile(phone_regex)
        if phone_pattern.match(phone):
            if "-" not in phone:
                phone = phone[:3] + "-" + phone[3:]
            if password1 and password2:
                if password1 == password2:
                    current_user.password=generate_password_hash(password1, method='pbkdf2')
                else:
                    flash('Passwords don\'t match.', category='error')
                    return redirect(url_for('views.profile'))
            current_user.phone = phone
            db.session.commit()
            flash('Update profile successfully!', category='success')
        else:
            flash('Invalid phone format!', category='error')
        
    return render_template("profile.html", user=current_user)

@views.route('/farm', methods=['GET', 'POST'])
@login_required
def farm():
    if request.method == 'POST':
        action =request.form.get('action')
        if action=="add":
            state = request.form.get('state')
            city = request.form.get('city')
            farm = request.form.get('farm')
            farm_exist = Farm.query.filter_by(name=farm,user_id=current_user.id).first()
            if not farm_exist:
                new_farm = Farm(name=farm,state=state,city=city,user_id=current_user.id)
                db.session.add(new_farm)
                db.session.commit()
                
                flash('Add farm successfully!', category='success')
                return render_template("farm.html", user=current_user, farm=current_user.farms)
            else:
                flash('Duplicate farm name is not allowed!', category='error')
                return render_template("farm.html", user=current_user, farm=current_user.farms)
            
        if action == "search":
            search = request.form.get('query')
            search = search.strip()

            query = db.session.query(Farm).filter(and_(func.lower(Farm.name + Farm.city + Farm.state).like(f"%{search.lower()}%"),Farm.user_id==current_user.id))
            farm_result = query.all()

            flash(f'Found {len(farm_result)} farms!', category='success')
            return render_template("farm.html", user=current_user, farm=farm_result)
        
        if action == "delete":
            farm_id = request.form.get('farm_id')
            farm = Farm.query.get(farm_id)
            if farm:
                if farm.user_id == current_user.id:
                    db.session.delete(farm)
                    db.session.commit()
        
            flash('Delete farm successfully!', category='success')
            return render_template("farm.html", user=current_user, farm=current_user.farms)

        
    return render_template("farm.html", user=current_user, farm=current_user.farms)

@views.route('/history', methods=['GET', 'POST'])
@login_required
def history():
    encoded_images = []
    if request.method == 'POST': 
        input = request.form.get('query')
        input = input.strip()

        history_data = History.query.filter(
            (History.label.ilike(f"%{input}%")) & (History.user_id == current_user.id)
        ).all()
        
        for history_item in history_data:
            img_bytes = history_item.img
            resized_image = resize_image(img_bytes, width=256, height=256)
            encoded_image = base64.b64encode(resized_image).decode('utf-8')
            encoded_images.append(encoded_image)

        flash(f'Found {len(history_data)} records.', category='success')
        return render_template("history.html", user=current_user,history=history_data, img=encoded_images)
        
    history_data = History.query.filter_by(user_id=current_user.id).all()

    for history_item in history_data:
        img_bytes = history_item.img
        resized_image = resize_image(img_bytes, width=256, height=256)
        encoded_image = base64.b64encode(resized_image).decode('utf-8')
        encoded_images.append(encoded_image)

    return render_template("history.html", user=current_user,history=current_user.histories, img=encoded_images)

@views.route('/<int:id>')
@login_required
def get_img(id):
    img = History.query.filter_by(id=id).first()
    if not img:
        flash('Image not found!', category='error')
        return redirect(url_for('views.detection'))
    return Response(img.img, mimetype=img.mimetype)
    
def get_ip():
    response = requests.get('https://api64.ipify.org?format=json').json()
    print("ip: ",response)
    return response["ip"]

def get_location():
    ip_address = get_ip()
    response = requests.get(f'https://ipinfo.io/{ip_address}/json/').json()
    print("response: ",response)
    location_data = {
        "ip": ip_address,
        "city": response.get("city"),
        "region": response.get("region"),
        "country": response.get("country")
    }
    return location_data

def resize_image(image_bytes, width, height):
    image = Image.open(BytesIO(image_bytes))

    resized_image = image.resize((width, height))

    output_buffer = BytesIO()
    resized_image.save(output_buffer, format="JPEG")
    resized_image_bytes = output_buffer.getvalue()

    return resized_image_bytes