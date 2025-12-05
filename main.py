import sys
import argparse
import os
from pathlib import Path
from typing import Optional


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.encryption_engine import EncryptionEngine
from core.decryption_engine import DecryptionEngine
from core.key_manager import KeyManager
from utils.logger import Logger
from utils.validator import Validator
from utils.file_handler import FileHandler
from config.settings import Settings


class DocumentEncryptionSystem:
    
    
    def __init__(self):
        self.logger = Logger()
        self.settings = Settings()
        self.validator = Validator()
        self.file_handler = FileHandler()
        self.key_manager = KeyManager()
        
        
        self._create_directories()
    
    def _create_directories(self):
        
        directories = [
            self.settings.ENCRYPTED_DIR,
            self.settings.DECRYPTED_DIR,
            self.settings.KEYS_DIR
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
        
        self.logger.info("Директории инициализированы")
    
    def encrypt_document(self, 
                        input_file: str, 
                        output_file: Optional[str] = None,
                        password: Optional[str] = None) -> dict:
        
        try:
            
            if not self.validator.validate_file(input_file):
                raise ValueError(f"Файл не найден или недоступен: {input_file}")
            
            
            file_type = self.validator.get_file_type(input_file)
            if not self.validator.is_supported_format(file_type):
                raise ValueError(f"Неподдерживаемый формат файла: {file_type}")
            
            self.logger.info(f"Начинается шифрование файла: {input_file}")
            self.logger.info(f"Тип файла: {file_type}")
            
            
            if password is None:
                password = self.key_manager.generate_master_password()
                self.logger.info("Сгенерирован мастер-пароль")
            
            
            encryption_engine = EncryptionEngine(
                password=password,
                key_manager=self.key_manager
            )
            
            
            file_data = self.file_handler.read_file(input_file)
            self.logger.info(f"Прочитано байт: {len(file_data)}")
            
            
            encrypted_data = encryption_engine.encrypt(
                data=file_data,
                file_type=file_type,
                original_filename=os.path.basename(input_file)
            )
            
            
            if output_file is None:
                output_file = self._generate_output_filename(
                    input_file, 
                    'encrypted',
                    self.settings.ENCRYPTED_DIR
                )
            
            
            self.file_handler.write_file(output_file, encrypted_data)
            self.logger.info(f"Зашифрованный файл сохранен: {output_file}")
            
            
            key_file = self._save_encryption_key(
                encryption_engine.get_key_bundle(),
                input_file
            )
            
            result = {
                'status': 'success',
                'input_file': input_file,
                'output_file': output_file,
                'key_file': key_file,
                'file_type': file_type,
                'original_size': len(file_data),
                'encrypted_size': len(encrypted_data),
                'compression_ratio': len(file_data) / len(encrypted_data) if len(encrypted_data) > 0 else 0
            }
            
            self.logger.info("Шифрование успешно завершено")
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка при шифровании: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def decrypt_document(self,
                        input_file: str,
                        key_file: str,
                        output_file: Optional[str] = None,
                        password: Optional[str] = None) -> dict:
        
        try:
            
            if not self.validator.validate_file(input_file):
                raise ValueError(f"Зашифрованный файл не найден: {input_file}")
            
            if not self.validator.validate_file(key_file):
                raise ValueError(f"Файл ключа не найден: {key_file}")
            
            self.logger.info(f"Начинается расшифровка файла: {input_file}")
            
            
            key_bundle = self.key_manager.load_key_bundle(key_file, password)
            self.logger.info("Ключи успешно загружены")
            
            
            decryption_engine = DecryptionEngine(
                key_bundle=key_bundle,
                key_manager=self.key_manager
            )
            
            
            encrypted_data = self.file_handler.read_file(input_file)
            self.logger.info(f"Прочитано зашифрованных байт: {len(encrypted_data)}")
            
            
            decrypted_result = decryption_engine.decrypt(encrypted_data)
            
            
            if output_file is None:
                output_file = self._generate_output_filename(
                    decrypted_result['original_filename'],
                    'decrypted',
                    self.settings.DECRYPTED_DIR
                )
            
            
            self.file_handler.write_file(output_file, decrypted_result['data'])
            self.logger.info(f"Расшифрованный файл сохранен: {output_file}")
            
            result = {
                'status': 'success',
                'input_file': input_file,
                'output_file': output_file,
                'original_filename': decrypted_result['original_filename'],
                'file_type': decrypted_result['file_type'],
                'encrypted_size': len(encrypted_data),
                'decrypted_size': len(decrypted_result['data'])
            }
            
            self.logger.info("Расшифровка успешно завершена")
            return result
            
        except Exception as e:
            self.logger.error(f"Ошибка при расшифровке: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }
    
    def _generate_output_filename(self, 
                                  input_file: str, 
                                  suffix: str,
                                  output_dir: str) -> str:
        
        base_name = os.path.basename(input_file)
        name_without_ext = os.path.splitext(base_name)[0]
        
        if suffix == 'encrypted':
            return os.path.join(output_dir, f"{name_without_ext}.encrypted")
        else:
            return os.path.join(output_dir, base_name)
    
    def _save_encryption_key(self, key_bundle: dict, original_file: str) -> str:
        
        base_name = os.path.basename(original_file)
        name_without_ext = os.path.splitext(base_name)[0]
        key_file = os.path.join(self.settings.KEYS_DIR, f"{name_without_ext}.key")
        
        self.key_manager.save_key_bundle(key_bundle, key_file)
        self.logger.info(f"Ключ сохранен: {key_file}")
        
        return key_file


def main():
    
    parser = argparse.ArgumentParser(
        description='Система шифрования документов с многоуровневой защитой',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  
  Шифрование:
    python main.py encrypt document.pdf
    python main.py encrypt report.docx --password mypassword
    python main.py encrypt data.xlsx --output custom_output.encrypted
  
  Расшифровка:
    python main.py decrypt document.encrypted --key document.key
    python main.py decrypt report.encrypted --key report.key --password mypassword
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Команды')
    
    
    encrypt_parser = subparsers.add_parser('encrypt', help='Зашифровать документ')
    encrypt_parser.add_argument('input', help='Путь к файлу для шифрования')
    encrypt_parser.add_argument('--output', '-o', help='Путь к выходному файлу')
    encrypt_parser.add_argument('--password', '-p', help='Пароль для шифрования')
    
    
    decrypt_parser = subparsers.add_parser('decrypt', help='Расшифровать документ')
    decrypt_parser.add_argument('input', help='Путь к зашифрованному файлу')
    decrypt_parser.add_argument('--key', '-k', required=True, help='Путь к файлу ключа')
    decrypt_parser.add_argument('--output', '-o', help='Путь к выходному файлу')
    decrypt_parser.add_argument('--password', '-p', help='Пароль для расшифровки ключа')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    
    system = DocumentEncryptionSystem()
    
    try:
        if args.command == 'encrypt':
            result = system.encrypt_document(
                input_file=args.input,
                output_file=args.output,
                password=args.password
            )
            
            if result['status'] == 'success':
                print("\n" + "="*70)
                print("[SUCCESS] ШИФРОВАНИЕ ВЫПОЛНЕНО УСПЕШНО")
                print("="*70)
                print(f"Входной файл:       {result['input_file']}")
                print(f"Зашифрованный файл: {result['output_file']}")
                print(f"Файл ключа:         {result['key_file']}")
                print(f"Тип файла:          {result['file_type']}")
                print(f"Исходный размер:    {result['original_size']:,} байт")
                print(f"Размер после:       {result['encrypted_size']:,} байт")
                print(f"Степень сжатия:     {result['compression_ratio']:.2f}x")
                print("="*70)
                print("\n[WARNING] ВАЖНО: Сохраните файл ключа! Без него расшифровка невозможна!")
                return 0
            else:
                print(f"\n[ERROR] Ошибка: {result['message']}")
                return 1
        
        elif args.command == 'decrypt':
            result = system.decrypt_document(
                input_file=args.input,
                key_file=args.key,
                output_file=args.output,
                password=args.password
            )
            
            if result['status'] == 'success':
                print("\n" + "="*70)
                print("[SUCCESS] РАСШИФРОВКА ВЫПОЛНЕНА УСПЕШНО")
                print("="*70)
                print(f"Входной файл:         {result['input_file']}")
                print(f"Расшифрованный файл:  {result['output_file']}")
                print(f"Оригинальное имя:     {result['original_filename']}")
                print(f"Тип файла:            {result['file_type']}")
                print(f"Размер зашифр.:       {result['encrypted_size']:,} байт")
                print(f"Размер расшифр.:      {result['decrypted_size']:,} байт")
                print("="*70)
                return 0
            else:
                print(f"\n[ERROR] Ошибка: {result['message']}")
                return 1
    
    except KeyboardInterrupt:
        print("\n\n[ERROR] Операция прервана пользователем")
        return 130
    except Exception as e:
        print(f"\n[ERROR] Критическая ошибка: {str(e)}")
        return 1


if __name__ == '__main__':
    sys.exit(main())