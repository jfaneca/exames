import os
import glob
import time
import getpass
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

# Gmail SMTP Settings
# To send emails using Gmail, you MUST use an App Password:
# 1. Go to your Google Account settings (https://myaccount.google.com/).
# 2. Select "Security" on the left menu.
# 3. Under "How you sign in to Google," make sure 2-Step Verification is enabled.
# 4. Click on "2-Step Verification" and scroll to the bottom.
# 5. Click on "App passwords" (if not visible, search for "App passwords" in the search box).
# 6. Generate a password for "Mail" and name it "Exames Sender".
# 7. Copy the generated 16-character password and use it here.
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "exames2526primeirafase.esgc@gmail.com"
BASE_DIR = "Listagem de Itens de Prova"

def send_email_with_attachments(recipient_email, student_name, pdf_paths, smtp_password):
    """
    Builds and sends an email with multiple PDF attachments using Gmail's SMTP server and App Password.
    """
    # Create the MIMEMultipart message container
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = recipient_email
    msg['Subject'] = f"Exames de {student_name}"

    # Email Body (in Portuguese)
    body = (
        f"Olá,\n\n"
        f"Seguem em anexo os ficheiros PDF correspondentes aos exames do(a) aluno(a) {student_name}.\n\n"
        f"Com os melhores cumprimentos,\n"
        f"Secretariado de Exames - ESGC"
    )
    msg.attach(MIMEText(body, 'plain', 'utf-8'))

    # Attach each PDF file
    for pdf_path in pdf_paths:
        filename = os.path.basename(pdf_path)
        try:
            with open(pdf_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                # Ensure the header is correctly encoded
                part.add_header(
                    'Content-Disposition',
                    'attachment',
                    filename=filename
                )
                msg.attach(part)
        except Exception as e:
            print(f"  -> Erro ao ler ou anexar o ficheiro {filename}: {e}")
            return False

    # Establish SMTP connection and send the email
    try:
        # Connect to Gmail SMTP Server (STARTTLS over port 587)
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20)
        server.ehlo()
        server.starttls()  # Upgrade connection to secure TLS
        server.ehlo()
        server.login(SENDER_EMAIL, smtp_password)
        server.sendmail(SENDER_EMAIL, recipient_email, msg.as_string())
        server.quit()
        return True
    except Exception as e:
        print(f"  -> Erro de conexão/autenticação SMTP para {recipient_email}: {e}")
        return False

def main():
    print("==================================================")
    print("      ENVIO AUTOMATIZADO DE EXAMES POR E-MAIL     ")
    print("==================================================")
    print(f"Remetente:  {SENDER_EMAIL}")
    print(f"Pasta Base: {BASE_DIR}\n")

    # Securely retrieve Gmail App Password (checks env variable first, then prompts user securely)
    smtp_password = os.environ.get("EMAIL_PASSWORD")
    smtp_password = "XXXXXXXXXXXXXXXX"
    if not smtp_password:
        smtp_password = getpass.getpass(prompt=f"Introduza a palavra-passe de aplicação do Gmail para {SENDER_EMAIL}: ")

    if not smtp_password:
        print("Palavra-passe não introduzida. Operação abortada.")
        return

    if not os.path.exists(BASE_DIR):
        print(f"Erro: A pasta '{BASE_DIR}' não foi encontrada.")
        return

    # List all subfolders in the base directory
    student_folders = [
        f for f in glob.glob(os.path.join(BASE_DIR, "*")) 
        if os.path.isdir(f)
    ]

    if not student_folders:
        print("Nenhuma pasta de aluno encontrada.")
        return

    print(f"Encontradas {len(student_folders)} pastas de alunos. Iniciando processamento...\n")

    success_count = 0
    fail_count = 0
    skipped_count = 0

    for idx, folder in enumerate(student_folders, 1):
        folder_name = os.path.basename(folder)
        
        # Extract student name (e.g., "ADELINA BRAGHIS - 26062908" -> "ADELINA BRAGHIS")
        if " - " in folder_name:
            student_name = folder_name.split(" - ")[0].strip()
        else:
            student_name = folder_name

        # Check if the "done" file already exists to prevent duplicate sends
        done_file_path = os.path.join(folder, "done")
        if os.path.exists(done_file_path):
            print(f"[{idx}/{len(student_folders)}] Pasta '{folder_name}' ignorada: E-mail já enviado anteriormente (ficheiro 'done' existe).")
            skipped_count += 1
            continue

        recipient_email = None
        pdf_files = []

        # Find the destination email and the PDF attachments in the directory
        for item in os.listdir(folder):
            item_path = os.path.join(folder, item)
            if os.path.isfile(item_path):
                if item.endswith(".piepe"):
                    # The name of the .piepe file is the recipient's email address
                    recipient_email = item[:-6].strip()
                elif item.endswith(".pdf"):
                    pdf_files.append(item_path)

        # Validation
        if not recipient_email:
            print(f"[{idx}/{len(student_folders)}] Pasta '{folder_name}' ignorada: Ficheiro .piepe (e-mail) em falta.")
            skipped_count += 1
            continue

        if not pdf_files:
            print(f"[{idx}/{len(student_folders)}] Pasta '{folder_name}' ignorada: Nenhum ficheiro PDF presente.")
            skipped_count += 1
            continue

        recipient_email = "XXXXX@esgc.pt"

        print(f"[{idx}/{len(student_folders)}] Enviando {len(pdf_files)} PDF(s) para {student_name} ({recipient_email})...")
        
        # Send the email
        success = send_email_with_attachments(recipient_email, student_name, pdf_files, smtp_password)
        
        if success:
            print("  -> E-mail enviado com sucesso!")
            # Create the 'done' marker file to prevent future duplicate sends
            try:
                with open(done_file_path, "w", encoding="utf-8") as df:
                    df.write(f"Enviado com sucesso em: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                print("  -> Ficheiro 'done' criado com sucesso.")
            except Exception as de:
                print(f"  -> Erro ao criar o ficheiro 'done': {de}")
            success_count += 1
        else:
            print("  -> FALHA no envio do e-mail.")
            fail_count += 1

        # Courteous delay to respect SMTP rate-limits and anti-spam controls
        time.sleep(2)

    print("\n==================================================")
    print("               RESUMO DO PROCESSO                 ")
    print("==================================================")
    print(f"Sucessos:  {success_count}")
    print(f"Falhas:    {fail_count}")
    print(f"Ignorados: {skipped_count}")
    print("==================================================")

if __name__ == "__main__":
    main()
