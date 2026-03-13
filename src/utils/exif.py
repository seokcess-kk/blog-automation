"""
EXIF 메타데이터 삽입 유틸리티

AI 생성 이미지에 실제 카메라로 촬영한 것처럼 EXIF 메타데이터를 삽입합니다.
PNG 이미지는 JPEG로 자동 변환됩니다.
"""

import logging
import os
import random
from datetime import datetime, timedelta
from typing import Optional

try:
    from PIL import Image
    import piexif
    EXIF_AVAILABLE = True
except ImportError:
    EXIF_AVAILABLE = False

logger = logging.getLogger(__name__)

# 지원하는 카메라 목록 (Make, Model)
CAMERAS: list[tuple[str, str]] = [
    ("Apple", "iPhone 14 Pro"),
    ("Apple", "iPhone 15"),
    ("Samsung", "SM-S918N"),  # Galaxy S23 Ultra
    ("Samsung", "SM-A546N"),  # Galaxy A54
    ("Samsung", "SM-S926N"),  # Galaxy S24+
]


def _generate_random_datetime(days_back_min: int = 1, days_back_max: int = 7) -> str:
    """최근 N일 내 랜덤 날짜/시간 생성 (EXIF 형식).

    Returns:
        EXIF DateTime 형식 문자열 (예: "2024:03:10 14:30:25")
    """
    days_back = random.randint(days_back_min, days_back_max)
    hours = random.randint(8, 20)  # 08:00 ~ 20:00
    minutes = random.randint(0, 59)
    seconds = random.randint(0, 59)

    target_date = datetime.now() - timedelta(days=days_back)
    target_date = target_date.replace(hour=hours, minute=minutes, second=seconds)

    return target_date.strftime("%Y:%m:%d %H:%M:%S")


def _convert_to_rational(value: float) -> tuple[tuple[int, int]]:
    """float 값을 EXIF rational 형식으로 변환.

    Args:
        value: 변환할 float 값

    Returns:
        단일 rational 값을 담은 튜플
    """
    # 간단한 변환: 소수점 4자리까지
    numerator = int(value * 10000)
    denominator = 10000
    return ((numerator, denominator),)


def _convert_gps_to_rational(
    coord: float,
) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    """GPS 좌표를 EXIF GPS 형식으로 변환.

    Args:
        coord: GPS 좌표 (위도 또는 경도)

    Returns:
        (degrees, minutes, seconds) 형식의 rational 튜플
    """
    coord_abs = abs(coord)
    degrees = int(coord_abs)
    minutes_float = (coord_abs - degrees) * 60
    minutes = int(minutes_float)
    seconds_float = (minutes_float - minutes) * 60
    seconds = int(seconds_float * 100)

    return (
        (degrees, 1),
        (minutes, 1),
        (seconds, 100),
    )


def inject_exif(
    image_path: str,
    output_path: str,
    region_gps: Optional[tuple[float, float]] = None,
) -> str:
    """AI 이미지에 카메라 EXIF 메타데이터 삽입.

    Args:
        image_path: 입력 이미지 경로
        output_path: 출력 이미지 경로 (JPEG)
        region_gps: GPS 좌표 (위도, 경도). None이면 GPS 정보 미삽입.
                    제공 시 미세 오프셋이 추가됨.

    Returns:
        저장된 출력 파일 경로

    Note:
        - PNG 입력 시 JPEG로 자동 변환 (EXIF는 JPEG만 지원)
        - 출력 경로 확장자가 .png면 자동으로 .jpg로 변경
    """
    if not EXIF_AVAILABLE:
        logger.warning("piexif/Pillow not installed. Skipping EXIF injection.")
        # 파일 복사만 수행
        import shutil
        shutil.copy2(image_path, output_path)
        return output_path

    # 출력 경로가 .png면 .jpg로 변경
    base, ext = os.path.splitext(output_path)
    if ext.lower() == ".png":
        output_path = base + ".jpg"
        logger.info(f"출력 형식을 PNG에서 JPEG로 변경: {output_path}")

    # 이미지 로드
    img = Image.open(image_path)

    # RGBA → RGB 변환 (JPEG는 알파 채널 미지원)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 랜덤 카메라 선택
    make, model = random.choice(CAMERAS)

    # 랜덤 날짜/시간 생성
    datetime_str = _generate_random_datetime()

    # 랜덤 초점거리 (24mm ~ 70mm)
    focal_length = random.randint(24, 70)

    # EXIF 데이터 구성
    exif_dict: dict = {
        "0th": {},
        "Exif": {},
        "GPS": {},
        "1st": {},
    }

    # 0th IFD (기본 정보)
    exif_dict["0th"][piexif.ImageIFD.Make] = make.encode("utf-8")
    exif_dict["0th"][piexif.ImageIFD.Model] = model.encode("utf-8")
    exif_dict["0th"][piexif.ImageIFD.Software] = b"blog-automation"
    exif_dict["0th"][piexif.ImageIFD.DateTime] = datetime_str.encode("utf-8")
    exif_dict["0th"][piexif.ImageIFD.Orientation] = 1

    # Exif IFD (촬영 정보)
    exif_dict["Exif"][piexif.ExifIFD.DateTimeOriginal] = datetime_str.encode("utf-8")
    exif_dict["Exif"][piexif.ExifIFD.DateTimeDigitized] = datetime_str.encode("utf-8")
    exif_dict["Exif"][piexif.ExifIFD.FocalLength] = (focal_length, 1)
    exif_dict["Exif"][piexif.ExifIFD.FocalLengthIn35mmFilm] = focal_length
    exif_dict["Exif"][piexif.ExifIFD.ColorSpace] = 1  # sRGB
    exif_dict["Exif"][piexif.ExifIFD.ExifVersion] = b"0232"

    # ISO 감도 (100 ~ 800 랜덤)
    iso = random.choice([100, 200, 400, 640, 800])
    exif_dict["Exif"][piexif.ExifIFD.ISOSpeedRatings] = iso

    # GPS 정보 (제공 시)
    if region_gps is not None:
        lat, lon = region_gps

        # 미세 오프셋 추가 (약 100m 이내)
        lat_offset = random.uniform(-0.001, 0.001)
        lon_offset = random.uniform(-0.001, 0.001)
        lat += lat_offset
        lon += lon_offset

        # 위도
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitudeRef] = (
            b"N" if lat >= 0 else b"S"
        )
        exif_dict["GPS"][piexif.GPSIFD.GPSLatitude] = _convert_gps_to_rational(lat)

        # 경도
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitudeRef] = (
            b"E" if lon >= 0 else b"W"
        )
        exif_dict["GPS"][piexif.GPSIFD.GPSLongitude] = _convert_gps_to_rational(lon)

        # GPS 버전
        exif_dict["GPS"][piexif.GPSIFD.GPSVersionID] = (2, 3, 0, 0)

    # EXIF 바이트로 변환
    exif_bytes = piexif.dump(exif_dict)

    # 이미지 저장 (EXIF 포함)
    img.save(output_path, "JPEG", quality=95, exif=exif_bytes)

    logger.info(
        f"EXIF 삽입 완료: {output_path} "
        f"(카메라: {make} {model}, 날짜: {datetime_str}, GPS: {region_gps is not None})"
    )

    return output_path
