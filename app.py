import os
from flask import Flask, render_template, request, send_file, redirect, url_for
from werkzeug.utils import secure_filename
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt
import io
import base64

# Инициализация приложения Flask
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB
app.config['SECRET_KEY'] = 'your-secret-key-here'  # Замените на свой секретный ключ

# Разрешенные расширения файлов
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Проверка расширения файла"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def rotate_image(image_path, angle):
    """Поворот изображения на заданный угол"""
    img = Image.open(image_path)
    rotated = img.rotate(int(angle), expand=True)
    return rotated

def create_color_histogram(img):
    """Создание гистограммы распределения цветов"""
    # Конвертируем изображение в numpy array
    if isinstance(img, str):
        img_array = np.array(Image.open(img))
    else:
        img_array = np.array(img)
    
    # Проверяем, есть ли цветовые каналы (для grayscale изображений)
    if len(img_array.shape) == 2:
        # Градации серого - один канал
        plt.figure(figsize=(6, 4))
        plt.hist(img_array.flatten(), bins=256, color='gray', alpha=0.7)
    else:
        # Цветное изображение - три канала (RGB)
        plt.figure(figsize=(6, 4))
        colors = ('red', 'green', 'blue')
        for i, color in enumerate(colors):
            hist = img_array[:, :, i].flatten()
            plt.hist(hist, bins=256, color=color, alpha=0.5, label=f'{color.upper()}')
        plt.legend()
    
    plt.title('Color Distribution')
    plt.xlabel('Pixel Intensity (0-255)')
    plt.ylabel('Frequency')
    plt.grid(True, alpha=0.3)
    
    # Сохраняем график в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    plt.close()
    buf.seek(0)
    return base64.b64encode(buf.read()).decode('utf-8')

@app.route('/')
def index():
    """Главная страница с формой загрузки"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_image():
    """Обработка загрузки изображения"""
    # Проверяем, есть ли файл в запросе
    if 'file' not in request.files:
        return redirect(request.url)
    
    file = request.files['file']
    angle = request.form.get('angle', 0)
    
    # Если файл не выбран
    if file.filename == '':
        return redirect(request.url)
    
    # Проверяем разрешенное расширение и сохраняем файл
    if file and allowed_file(file.filename):
        # Создаем папку для загрузок, если ее нет
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Сохраняем оригинальное изображение
        filename = secure_filename(file.filename)
        original_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(original_path)
        
        # Поворачиваем изображение
        rotated_img = rotate_image(original_path, angle)
        
        # Сохраняем повернутое изображение
        rotated_filename = f'rotated_{filename}'
        rotated_path = os.path.join(app.config['UPLOAD_FOLDER'], rotated_filename)
        rotated_img.save(rotated_path)
        
        # Создаем гистограммы
        original_hist = create_color_histogram(original_path)
        rotated_hist = create_color_histogram(rotated_img)
        
        # Передаем данные в шаблон результата
        return render_template('result.html',
                               original=original_path,
                               rotated=rotated_path,
                               angle=angle,
                               original_filename=filename,
                               rotated_filename=rotated_filename,
                               original_hist=original_hist,
                               rotated_hist=rotated_hist)
    
    return 'Invalid file type. Please upload PNG, JPG, or JPEG.'

@app.route('/process', methods=['POST'])
def process_image():
    """API endpoint для обработки изображения (для AJAX запросов)"""
    if 'file' not in request.files:
        return {'error': 'No file provided'}, 400
    
    file = request.files['file']
    angle = request.form.get('angle', 45)
    
    if file and allowed_file(file.filename):
        # Сохраняем временный файл
        filename = secure_filename(file.filename)
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'temp_{filename}')
        file.save(temp_path)
        
        # Обрабатываем изображение
        rotated_img = rotate_image(temp_path, angle)
        
        # Создаем гистограмму
        histogram = create_color_histogram(rotated_img)
        
        # Сохраняем результат
        result_filename = f'processed_{filename}'
        result_path = os.path.join(app.config['UPLOAD_FOLDER'], result_filename)
        rotated_img.save(result_path)
        
        # Удаляем временный файл
        os.remove(temp_path)
        
        return {
            'success': True,
            'image_url': url_for('static', filename=f'uploads/{result_filename}'),
            'histogram': histogram,
            'angle': angle
        }
    
    return {'error': 'Invalid file type'}, 400

@app.route('/api/info')
def api_info():
    """Информация об API"""
    return {
        'name': 'Image Processing API',
        'version': '1.0',
        'endpoints': {
            '/': 'Main page with upload form',
            '/upload': 'POST - Upload and process image',
            '/process': 'POST - API endpoint for image processing',
            '/api/info': 'GET - API information'
        },
        'supported_formats': list(ALLOWED_EXTENSIONS)
    }

@app.route('/health')
def health_check():
    """Endpoint для проверки работоспособности"""
    return {'status': 'healthy', 'service': 'Flask Image Processor'}

# Запуск приложения
if __name__ == '__main__':
    # Создаем папку для загрузок при запуске
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Запускаем сервер
    app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000)),
        debug=os.environ.get('FLASK_ENV') == 'development'
    )