from flask import Flask, request, send_file, render_template, jsonify
import subprocess
import os
import uuid
import threading
import time

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

UPLOAD_FOLDER = '/tmp/ppt2pdf'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def cleanup_file(path, delay=300):
    def _delete():
        time.sleep(delay)
        try:
            if os.path.isfile(path):
                os.remove(path)
            elif os.path.isdir(path):
                import shutil
                shutil.rmtree(path)
        except:
            pass
    threading.Thread(target=_delete, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert():
    if 'file' not in request.files:
        return jsonify({'error': 'Koi file nahi mili'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'File select karo'}), 400

    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ['.ppt', '.pptx']:
        return jsonify({'error': 'Sirf .ppt ya .pptx file upload karo'}), 400

    uid = str(uuid.uuid4())
    input_path = os.path.join(UPLOAD_FOLDER, f"{uid}{ext}")
    output_dir = os.path.join(UPLOAD_FOLDER, uid + '_out')
    os.makedirs(output_dir, exist_ok=True)
    file.save(input_path)

    try:
        result = subprocess.run(
            ['libreoffice', '--headless', '--convert-to', 'pdf',
             '--outdir', output_dir, input_path],
            capture_output=True, text=True, timeout=120
        )

        pdf_name = os.path.splitext(os.path.basename(input_path))[0] + '.pdf'
        pdf_path = os.path.join(output_dir, pdf_name)

        if not os.path.exists(pdf_path):
            app.logger.error(f"STDOUT: {result.stdout}")
            app.logger.error(f"STDERR: {result.stderr}")
            return jsonify({'error': 'Conversion fail hui. LibreOffice error.'}), 500

        cleanup_file(input_path)
        cleanup_file(output_dir)

        download_name = os.path.splitext(file.filename)[0] + '.pdf'
        return send_file(pdf_path, mimetype='application/pdf',
                         as_attachment=True, download_name=download_name)

    except FileNotFoundError:
        return jsonify({'error': 'LibreOffice server pe install nahi hai'}), 500
    except subprocess.TimeoutExpired:
        return jsonify({'error': 'Timeout — file bahut badi hai'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
