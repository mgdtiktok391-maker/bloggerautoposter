# -*- coding: utf-8 -*-
import os, re, time, random, json, html, hashlib
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo

import requests
import backoff
import feedparser
from apscheduler.schedulers.background import BackgroundScheduler

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

import markdown as md
import bleach

from flask import Flask, request, jsonify

# =================== إعدادات عامة ===================
TZ = ZoneInfo("Asia/Baghdad")
POST_TIMES_LOCAL = ["10:00", "18:00"]  # يوميًا بتوقيت بغداد (صباح / مساء)

SAFE_CALLS_PER_MIN = int(os.getenv("SAFE_CALLS_PER_MIN", "3"))
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "3"))
AI_BACKOFF_BASE = int(os.getenv("AI_BACKOFF_BASE", "4"))

# أسرار أساسية
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
BLOG_URL = os.environ["BLOG_URL"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REFRESH_TOKEN = os.environ["REFRESH_TOKEN"]

# أسرار اختيارية للصور
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY", "")
PIXABAY_API_KEY = os.getenv("PIXABAY_API_KEY", "")
UNSPLASH_ACCESS_KEY = os.getenv("UNSPLASH_ACCESS_KEY", "")
FORCED_IMAGE = os.getenv("FEATURED_IMAGE_URL", "").strip()

# ترند: دولة واحدة أو قائمة دول
TREND_GEO = os.getenv("TREND_GEO", "IQ")
TREND_GEO_LIST = [
    g.strip() for g in os.getenv("TREND_GEO_LIST", "").split(",") if g.strip()
]

# منع التكرار موضوعيًا عبر عدد أيام
TOPIC_WINDOW_D = int(os.getenv("TOPIC_WINDOW_DAYS", "14"))

# =================== سياسة اختيار المواضيع (اختياري) ===================
_TOPIC_POLICY = os.getenv("TOPIC_POLICY", "")
POLICY = {
    "avoid_repeat":
    "true" in _TOPIC_POLICY,
    "diversification":
    "high" in _TOPIC_POLICY,
    "allow_old_topics_after_days":
    int(re.search(r"after_days:(\d+)", _TOPIC_POLICY or "")[1]) if re.search(
        r"after_days:(\d+)", _TOPIC_POLICY or "") else 90,
    "prefer_new_domains":
    "true" in _TOPIC_POLICY,
    "trend_mix":
    float(re.search(r"trend_mix:(\d+(?:\.\d+)?)", _TOPIC_POLICY or "")[1])
    if re.search(r"trend_mix:(\d+(?:\.\d+)?)", _TOPIC_POLICY or "") else 0.4
}


def should_skip_topic(topic_key: str) -> bool:
    if not POLICY["avoid_repeat"]:
        return False
    cutoff = datetime.now(TZ) - timedelta(
        days=POLICY["allow_old_topics_after_days"])
    for rec in load_jsonl(HISTORY_TOPICS_FILE):
        try:
            if rec.get("topic_key") == topic_key and datetime.fromisoformat(
                    rec["time"]) > cutoff:
                return True
        except:
            pass
    return False


def diversify_topic_request(category: str) -> str:
    base = f"فئة المقال: {category}\n"
    if POLICY["diversification"]:
        base += "اختر مجالًا جديدًا لم يتم تناوله مؤخرًا، استكشف زاوية غير مألوفة.\n"
    if POLICY["prefer_new_domains"]:
        base += "اختر مواضيع من مجالات ناشئة أو متطورة حديثًا بدل المواضيع التقليدية.\n"
    return base


# وضع التشغيل
PUBLISH_MODE = os.getenv("PUBLISH_MODE", "live").lower()  # draft | live
RUN_ONCE = os.getenv("RUN_ONCE", "0") == "1"

# هل نُحدّث المنشور إذا تكرر العنوان
UPDATE_IF_TITLE_EXISTS = (os.getenv("UPDATE_IF_TITLE_EXISTS", "0") == "1")

# تشغيل عبر كرون خارجي (Webhook)
USE_EXTERNAL_CRON = os.getenv("USE_EXTERNAL_CRON", "0") == "1"
TRIGGER_TOKEN = os.getenv("TRIGGER_TOKEN", "")  # اختر كلمة سر قوية

# REST (Gemini)
GEMINI_API_ROOT = "https://generativelanguage.googleapis.com"
GEN_CONFIG = {"temperature": 0.7, "topP": 0.9, "maxOutputTokens": 4096}

# سجلات محلية
HISTORY_TITLES_FILE = "posted_titles.jsonl"
HISTORY_TOPICS_FILE = "used_topics.jsonl"
TITLE_WINDOW = int(os.getenv("TITLE_WINDOW", "40"))

# Flask (لخيار الكرون الخارجي)
app = Flask(__name__)

# =================== قوائم مواضيع جاهزة ===================
TOPICS_TECH = [
    "حل مشكلة بطء الإنترنت وتسريع الواي فاي Wi-Fi Speed Optimization",
    "استعادة الملفات المحذوفة من الهاتف والكمبيوتر Data Recovery Tools",
    "حل مشكلة امتلاء ذاكرة الهاتف دون حذف صور Storage Space Cleanup",
    "طريقة تتبع الهاتف المسروق واستعادته Find My Device Guide",
    "إزالة الفيروسات من الكمبيوتر نهائياً Antivirus Removal Steps",
    "حل مشكلة الشاشة الزرقاء في ويندوز Windows Blue Screen Fix",
    "تسريع الهاتف الأندرويد القديم وجعله كالجديد Android Performance Boost",
    "حماية الواتساب من الاختراق والتجسس WhatsApp Security Verification",
    "طرق تجاوز نسيان كلمة سر الهاتف Unlock Android Password",
    "أفضل إعدادات راوتر للحصول على سرعة قصوى Router Configuration Best Settings",
    "تحويل الهاتف إلى كاميرا ويب للكمبيوتر Phone to Webcam",
    "حل مشكلة استنزاف البطارية بسرعة Battery Life Saving Tips",
    "نقل البيانات من أيفون إلى أندرويد والعكس Phone Data Transfer",
    "استرجاع حساب فيسبوك المسروق أو المعطل Recover Hacked Facebook",
    "طريقة فرمتة الكمبيوتر وتثبيت ويندوز Windows 10/11 Installation",
    "تشغيل تطبيقات الأندرويد على الكمبيوتر Android Emulators for PC",
    "حل مشكلة سخونة الهاتف أثناء اللعب Phone Overheating Solutions",
    "تحديث تعريفات الكمبيوتر تلقائياً Driver Update Tools",
    "معرفة مواصفات جهازك الحقيقية وكشف التقليد Hardware Specs Check",
    "إصلاح الفلاش ميموري التالفة التي لا تقرأ Fix Corrupted USB Drive",
    "أسرار البحث في جوجل للوصول للنتائج بدقة Google Search Tricks",
    "تحميل الفيديوهات من يوتيوب وفيسبوك Video Downloader Guide",
    "ضغط ملفات PDF وتقليل حجمها دون فقد الجودة Compress PDF Online",
    "تسجيل شاشة الكمبيوتر فيديو بجودة عالية Screen Recorder Software",
    "حل مشكلة عدم ظهور الهارد ديسك External Hard Drive Not Recognized",
    "طريقة عمل روت للهاتف: المميزات والعيوب Android Rooting Guide",
    "تغيير عنوان IP وفتح المواقع المحجوبة VPN Free Unlimited",
    "إلغاء الإعلانات المزعجة في الهاتف والمتصفح Block Ads Permanently",
    "طريقة معرفة من متصل معك بالشبكة وفصله Who Is On My WiFi",
    "إصلاح مشكلة الصوت لا يعمل في الكمبيوتر No Audio Output Fix",
    "كيفية إنشاء موقع إلكتروني مجاني خطوة بخطوة Create Free Website",
    "أفضل تطبيقات المونتاج للهاتف للمبتدئين Video Editing Apps",
    "التحقق من حالة بطارية الآيفون iPhone Battery Health",
    "حل مشكلة التطبيق ليس مثبتاً App Not Installed Error",
    "كيفية عمل بريد إلكتروني احترافي للشركات Professional Email Setup",
    "طريقة تفعيل الوضع الليلي في كل التطبيقات Force Dark Mode",
    "حل مشكلة توقف المتجر Google Play Services Error",
    "كيفية تشفير الملفات الحساسة بكلمة سر Encrypt Files Folder",
    "الفرق بين أنواع شاشات الهواتف OLED vs LCD vs AMOLED",
    "طرق تبريد اللابتوب ومنع صوت المروحة Laptop Cooling Pad",
    "كيفية استخدام الهاتف كريموت كونترول Phone as TV Remote",
    "أفضل برامج استعادة الصور القديمة بجودة عالية AI Photo Restoration",
    "كيفية قراءة الرسائل المحذوفة في واتساب Read Deleted Messages",
    "حل مشكلة بطء الألعاب واللاج Game Booster Optimization",
    "طريقة حرق الويندوز على فلاشة Rufus Bootable USB",
    "كيفية معرفة سرعة الإنترنت الحقيقية Internet Speed Test",
    "حل مشكلة عدم شحن الهاتف أو الشحن البطيء Phone Not Charging Fix",
    "أفضل بدائل برامج أوفيس المجانية Free Office Alternatives",
    "كيفية دمج تقسيمات الهارد ديسك Partition Magic Tool",
    "طريقة إخفاء التطبيقات والصور في الهاتف Hide Apps Android",
    "حل مشكلة لوحة المفاتيح لا تكتب Keyboard Not Working",
    "كيفية توصيل الهاتف بالتلفزيون Screen Mirroring Guide",
    "أفضل متصفح للخصوصية ومنع التتبع Private Browser Brave",
    "طريقة إرسال ملفات كبيرة الحجم مجاناً Large File Transfer",
    "حل مشكلة الكاميرا لا تعمل في زووم Webcam Fix Zoom",
    "كيفية تنظيف سماعات الهاتف من الغبار والماء Speaker Cleaner Sound",
    "أفضل إضافات جوجل كروم لزيادة الإنتاجية Best Chrome Extensions",
    "طريقة عمل نسخة احتياطية للواتساب كاملة WhatsApp Backup Restore",
    "كيفية فحص الرابط قبل الدخول عليه Link Virus Scanner",
    "حل مشكلة المثلث الأصفر في الاتصال No Internet Access Fix"
]

TOPICS_SCIENCE = [
    "أسباب الشعور بالتعب الدائم رغم النوم Chronic Fatigue Syndrome",
    "فوائد الصيام المتقطع علمياً للتخسيس Intermittent Fasting Science",
    "حقيقة وجود كائنات فضائية وأحدث الأدلة Extraterrestrial Life Evidence",
    "لماذا نرى الأحلام؟ تفسير علم الأعصاب Dream Psychology Science",
    "أعراض نقص فيتامين د وتأثيره على النفسية Vitamin D Deficiency",
    "ظاهرة الديجافو: لماذا تشعر أنك عشت الموقف سابقاً؟ Déjà Vu Explained",
    "كيف يؤثر الضوء الأزرق على جودة نومك؟ Blue Light Sleep Impact",
    "أسرار الثقوب السوداء وماذا يوجد داخلها؟ Black Holes Mystery",
    "هل الذكاء وراثي أم مكتسب؟ Genetics vs Environment IQ",
    "تأثير السكر على الدماغ والإدمان Sugar Addiction Science",
    "كيف تتكون الذاكرة وكيف نقويها؟ Memory Formation Neuroscience",
    "العلاج بالتبريد وفوائده للرياضيين Cryotherapy Benefits",
    "ما هو الميكروبيوم وعلاقته بالمناعة؟ Gut Microbiome Health",
    "حقيقة الاحتباس الحراري وهل فات الأوان؟ Climate Change Facts",
    "كيف تعمل اللقاحات في جسم الإنسان؟ mRNA Vaccine Mechanism",
    "علم لغة الجسد: كيف تقرأ أفكار الآخرين؟ Body Language Science",
    "تأثير التأمل على تركيب الدماغ Meditation Brain Changes",
    "لماذا نشعر بالقشعريرة؟ الأسباب العلمية Goosebumps Reason",
    "هل يمكن عكس الشيخوخة علمياً؟ Anti-Aging Research",
    "أضرار الجلوس لفترات طويلة على الصحة Sitting Disease Risks",
    "كيف يؤثر التوتر المزمن على أعضاء الجسم؟ Chronic Stress Effects",
    "الفرق العلمي بين القلق والاكتئاب Anxiety vs Depression",
    "ظاهرة شلل النوم (الجاثوم) تفسيرها وعلاجها Sleep Paralysis",
    "ما هي المادة المظلمة التي تملأ الكون؟ Dark Matter Mystery",
    "فوائد الاستحمام بالماء البارد علمياً Cold Shower Benefits",
    "كيف يختار الدماغ القرارات في أجزاء من الثانية؟ Decision Making Brain",
    "تأثير الموسيقى على التركيز والإنتاجية Music and Focus Science",
    "هل يمكن العيش على كوكب المريخ؟ Mars Colonization Challenges",
    "علم الوراثة: كيف تنتقل الصفات للأبناء؟ DNA Heredity Basics",
    "أسباب الصداع النصفي وطرق تخفيفه Migraine Triggers Science",
    "ما هو الانفجار العظيم وكيف بدأ الكون؟ Big Bang Theory",
    "تأثير الكافيين على الجهاز العصبي Caffeine Metabolism",
    "لماذا تتغير أصواتنا عندما نكبر؟ Voice Changing Science",
    "ظاهرة السراب كيف تحدث فيزيائياً؟ Mirage Physics Explanation",
    "كيف تطير الطائرات الثقيلة؟ مبادئ الديناميكا Aerodynamics Basics",
    "الذكاء الاصطناعي وهل يمتلك وعياً؟ AI Consciousness Debate",
    "تأثير الصيام على تجديد الخلايا Autophagy Process",
    "لماذا لون السماء أزرق ولون الغروب أحمر؟ Light Scattering Physics",
    "كيف يعمل الليزك لتصحيح النظر؟ LASIK Eye Surgery",
    "ما هو الاندماج النووي (طاقة المستقبل)؟ Nuclear Fusion Energy",
    "تأثير الوحدة العزلة على الصحة العقلية Loneliness Health Risks",
    "كيف تتواصل الأشجار مع بعضها؟ Plant Communication Network",
    "أسرار مثلث برمودا والنظريات العلمية Bermuda Triangle Theories",
    "لماذا ننسى أسماء الأشخاص فوراً؟ Forgetting Names Psychology",
    "تأثير البلاستيك الدقيق على جسم الإنسان Microplastics In Blood",
    "كيف يحدث البرق والرعد؟ Thunderstorm Physics",
    "هل الماء يمتلك ذاكرة؟ Water Memory Pseudoscience",
    "علم الأوبئة: كيف تنتشر الفيروسات؟ Epidemiology Basics",
    "ما هي الخلايا الجذعية وقدرتها العلاجية Stem Cell Therapy",
    "كيف يؤثر القمر على المد والجزر وسلوك البشر؟ Moon Effect Science",
    "لماذا نشعر بالدوار عند الوقوف فجأة؟ Orthostatic Hypotension",
    "تفسير ظاهرة الاحتراق النفسي Job Burnout Symptoms",
    "كيف يعمل التخدير في العمليات الجراحية؟ Anesthesia Mechanism",
    "تأثير الألوان على الحالة المزاجية Color Psychology",
    "ما هو الصوت وكيف نسمعه؟ Sound Waves Physics",
    "هل يمكن السفر عبر الزمن نظرياً؟ Time Travel Physics",
    "تأثير قلة النوم على الوزن والهرمونات Sleep Deprivation Obesity",
    "كيف تعمل الألواح الشمسية؟ Photovoltaic Cells Physics",
    "العلاقة بين الأمعاء والدماغ (المخ الثاني) Gut-Brain Axis",
    "لماذا نشعر بالألم؟ علم الأعصاب Pain Perception Science"
]

TOPICS_SOCIAL = [
    "كيف تبدأ العمل الحر (الفريلانس) من الصفر؟ Freelancing for Beginners",
    "طرق الربح من الإنترنت للمبتدئين بدون رأس مال Passive Income Ideas",
    "كيفية كتابة سيرة ذاتية CV مقبولة عالمياً ATS Resume Writing",
    "أهم مهارات المستقبل التي يطلبها سوق العمل Future Job Skills",
    "كيفية الهجرة إلى كندا: الشروط والخطوات Canada Immigration Guide",
    "كيف تتعامل مع الشخصية النرجسية؟ Narcissistic Personality Dealing",
    "خطوات إنشاء مشروع تجاري ناجح Small Business Startup",
    "كيف تدير راتبك الشهري وتوفر منه؟ Personal Budgeting Tips",
    "الفرق بين العملة الرقمية والعملة الورقية Cryptocurrency vs Fiat",
    "كيفية الحصول على منحة دراسية ممولة بالكامل Full Scholarship Guide",
    "فن الإقناع والتفاوض في الحياة والعمل Negotiation Skills",
    "كيفية التخلص من التسويف والمماطلة Overcoming Procrastination",
    "نصائح للمقابلة الشخصية (الإنترفيو) لضمان الوظيفة Job Interview Tips",
    "العمل عن بعد: الوظائف الأكثر طلباً Remote Work Jobs",
    "كيفية بناء الثقة بالنفس وقوة الشخصية Building Self-Confidence",
    "طرق الاستثمار في الذهب والأسهم للمبتدئين Investing for Beginners",
    "كيف تختار شريك الحياة المناسب؟ Relationship Compatibility",
    "تأثير التضخم على مدخراتك وكيف تحميها Inflation Protection",
    "تعلم اللغة الإنجليزية ذاتياً من المنزل Self-Study English Guide",
    "كيفية التسويق لنفسك وبناء علامة شخصية Personal Branding",
    "كيف تكتشف شغفك الحقيقي في الحياة؟ Finding Your Passion",
    "قوانين العمل وحقوق الموظف التي يجب معرفتها Labor Law Basics",
    "كيفية التعامل مع ضغوط العمل والمدير الصعب Toxic Work Environment",
    "خطوات شراء أول منزل: نصائح عقارية First Time Home Buyer",
    "كيف تصبح صانع محتوى ناجح على يوتيوب Content Creator Guide",
    "أهمية الذكاء العاطفي في النجاح المهني Emotional Intelligence at Work",
    "كيف تخطط لمستقبلك المالي والتقاعد؟ Retirement Planning",
    "الفرق بين الادخار والاستثمار وأيهما أفضل؟ Saving vs Investing",
    "كيفية التعامل مع الفشل والبدء من جديد Resilience Building",
    "نصائح للسفر بأقل التكاليف (سفر اقتصادي) Budget Travel Tips",
    "كيفية الحصول على فيزا شنغن لأوروبا Schengen Visa Requirements",
    "مهارات القيادة: كيف تكون مديراً ناجحاً؟ Leadership Skills",
    "كيف تحمي أطفالك من مخاطر الإنترنت؟ Internet Safety for Kids",
    "إدارة الوقت: كيف تنجز مهام أكثر في وقت أقل Time Management Techniques",
    "كيفية كتابة إيميل رسمي احترافي Professional Email Etiquette",
    "العمل التطوعي وأثره على السيرة الذاتية Volunteering Benefits",
    "كيف تتخلص من العادات السيئة وتبني عادات جيدة؟ Habit Tracking",
    "التجارة الإلكترونية: كيف تفتح متجر أونلاين؟ E-commerce DropShipping",
    "كيفية التعامل مع التنمر في المدرسة والعمل Dealing with Bullying",
    "ثقافة الاستهلاك: كيف تشتري ما تحتاجه فقط؟ Minimalist Living",
    "كيفية التحضير لاختبار الآيلتس IELTS Exam Preparation",
    "مهارات التواصل الفعال مع الآخرين Effective Communication",
    "كيف تبني شبكة علاقات مهنية قوية؟ Professional Networking",
    "نصائح للطلاب الجامعيين للتفوق الدراسي University Study Tips",
    "كيفية حل الخلافات الزوجية بطريقة صحية Marital Conflict Resolution",
    "العملات المشفرة: هل هي استثمار آمن؟ Crypto Investment Risks",
    "كيف تؤثر السوشيال ميديا على الصحة النفسية؟ Social Media Detox",
    "خطوات تسجيل براءة اختراع لحماية فكرتك Patent Registration Steps",
    "كيفية طلب زيادة في الراتب بذكاء Salary Negotiation Tips",
    "الفرق بين القائد والمدير Leader vs Manager",
    "كيف تتغلب على الخوف من التحدث أمام الجمهور Public Speaking Fear",
    "أهمية القراءة وكيف تجعلها عادة يومية Reading Habits",
    "كيفية التعامل مع الرفض في العمل والحياة Dealing with Rejection",
    "نصائح لتربية الأطفال في العصر الرقمي Modern Parenting Tips",
    "كيف تحافظ على التوازن بين العمل والحياة Work-Life Balance",
    "أفضل طرق للدفع الإلكتروني الآمن Online Payment Security",
    "كيفية كتابة خطة عمل لمشروعك Business Plan Writing",
    "مهارات التفكير النقدي وحل المشكلات Critical Thinking Skills",
    "كيف تختار التخصص الجامعي المناسب؟ Choosing College Major",
    "مستقبل الوظائف: ما هي المهن التي ستختفي؟ AI Impact on Jobs"
]

TOPICS_AI = [
    "شرح ChatGPT لكتابة المقالات والأبحاث ChatGPT for Writing",
    "كيفية تصميم صور خيالية باستخدام Midjourney AI Art Generator",
    "استخدام Notion AI لتنظيم العمل وزيادة الإنتاجية Productivity Tools",
    "تحويل النص إلى صوت احترافي باستخدام ElevenLabs Text to Speech",
    "كيفية إنشاء عرض تقديمي كامل بالذكاء الاصطناعي Tome AI Slides",
    "استخدام Bing Chat للبحث المتطور والمقارنة AI Search Engine",
    "أداة Adobe Firefly للتعديل على الصور بالذكاء الاصطناعي AI Photo Editing",
    "كيفية تلخيص ملفات PDF الطويلة باستخدام ChatPDF Document Analysis",
    "إنشاء فيديو من النص باستخدام Runway Gen-2 AI Video Generation",
    "استخدام GitHub Copilot للمساعدة في البرمجة AI Coding Assistant",
    "كيفية إزالة الخلفية من الصور بدقة عالية Remove.bg AI Tool",
    "أداة Grammarly لتصحيح الأخطاء اللغوية وتحسين الكتابة AI Grammar Checker",
    "استخدام Canva Magic Edit لتصميم الجرافيك Canva AI Tools",
    "كيفية تلوين الصور القديمة الأبيض والأسود Palette.fm AI Colorizer",
    "أداة Otter.ai لتحويل الكلام في الاجتماعات إلى نص Meeting Transcriber",
    "استخدام Perplexity AI كمحرك بحث ذكي للإجابات الدقيقة AI Research Tool",
    "كيفية تأليف الموسيقى والألحان باستخدام Soundraw AI Music Generator",
    "أداة Synthesia لإنشاء مذيع افتراضي يتحدث بالفيديو AI Avatars",
    "استخدام Leonardo.ai كبديل مجاني لتصميم الصور AI Image Free",
    "كيفية تحسين جودة الصور المشوشة باستخدام Remini AI Enhancer",
    "أداة Copy.ai لكتابة إعلانات ومنشورات تسويقية AI Copywriting",
    "استخدام Google Bard (Gemini) في تحليل البيانات Gemini AI Features",
    "كيفية عزل الصوت وإزالة الضوضاء من الفيديو Adobe Podcast AI",
    "أداة Beautiful.ai لتصميم شرائح العرض تلقائياً AI Presentation Maker",
    "استخدام Quillbot لإعادة صياغة النصوص وتجنب السرقة الأدبية Paraphrasing Tool",
    "كيفية استخراج المعلومات من البيانات الضخمة Julius AI Data Analyst",
    "أداة Looka لتصميم شعار (لوجو) احترافي للشركات AI Logo Maker",
    "استخدام Murf.ai للتعليق الصوتي بلهجات مختلفة AI Voiceover",
    "كيفية إنشاء موقع كامل في ثواني باستخدام Durable AI Website Builder",
    "أداة Writesonic لكتابة مقالات متوافقة مع السيو SEO AI Writer",
    "استخدام Jasper AI للمحتوى التسويقي الطويل AI Marketing Tools",
    "كيفية تحويل رسمة يدوية إلى صورة واقعية Scribble Diffusion AI",
    "أداة Descript لتحرير الفيديو عن طريق تعديل النص Video Text Editing",
    "استخدام Poe للوصول لكل بوتات الذكاء الاصطناعي في مكان واحد All-in-One AI",
    "كيفية ترجمة الفيديوهات للغات أخرى بنفس الصوت HeyGen Video Translate",
    "أداة Clipdrop من جوجل لتعديل الإضاءة في الصور AI Relight",
    "استخدام Gamma لإنشاء مستندات وعروض ويب AI Documents",
    "كيفية البحث عن أوراق بحثية علمية باستخدام Consensus AI Research",
    "أداة Speechify لقراءة الكتب والمقالات بصوت مسموع Text to Audio",
    "استخدام PhotoRoom لصور منتجات احترافية للمتاجر AI Product Photography",
    "كيفية تصميم ديكور غرفة باستخدام Interior AI Room Design",
    "أداة InVideo لتحويل السكريبت إلى فيديو يوتيوب Text to Video AI",
    "استخدام Claude 2 لتحليل النصوص الطويلة جداً AI Context Analysis",
    "كيفية استعادة تفاصيل الوجه في الصور القديمة GFP-GAN AI Restoration",
    "أداة Suno AI لتأليف أغاني كاملة بالكلمات واللحن AI Song Generator",
    "استخدام Krisp لإلغاء ضجيج الخلفية في المكالمات Noise Cancellation",
    "كيفية تحويل الفيديو الطويل إلى مقاطع قصيرة Opus Clip AI Shorts",
    "أداة CodeInterpreter لتحليل ملفات الإكسل والبيانات Data Science AI",
    "استخدام Stable Diffusion لتوليد الصور محلياً Open Source AI Art",
    "كيفية التعلم مع Khan Academy Khanmigo المعلم الذكي AI Tutor"
]

# =================== أدوات نص/HTML ===================
def clamp_words_ar(text, min_words=1000, max_words=1400):
    words = text.split()
    if len(words) < min_words: return text
    if len(words) <= max_words: return text
    clipped = " ".join(words[:max_words])
    m = re.search(r"(.+[.!؟…])", clipped, flags=re.S)
    return m.group(1) if m else clipped


def strip_code_fences(text):
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"<script.*?>.*?</script>", "", text, flags=re.I | re.S)
    text = re.sub(r"<style.*?>.*?</style>", "", text, flags=re.I | re.S)
    return text


def markdown_to_clean_html(md_text):
    html_raw = md.markdown(md_text, extensions=["extra", "sane_lists"])
    allowed = bleach.sanitizer.ALLOWED_TAGS.union({
        "p", "h2", "h3", "h4", "h5", "h6", "blockquote", "ul", "ol", "li",
        "strong", "em", "a", "img", "hr", "br", "code", "pre"
    })
    attrs = {
        "a": ["href", "title", "rel", "target"],
        "img":
        ["src", "alt", "title", "loading", "decoding", "width", "height"],
    }
    clean = bleach.clean(
        html_raw,
        tags=allowed,
        attributes=attrs,
        protocols=["http", "https", "mailto"],
        strip=True,
    )
    clean = clean.replace("<a ", '<a target="_blank" rel="noopener" ')
    return clean


def linkify_urls_md(text: str) -> str:
    return re.sub(r'(?<!\()https?://[^\s)]+',
                  lambda m: f"[المصدر]({m.group(0)})", text)


# =================== تاريخ ومنع تكرار (محلي + Blogger) ===================
def norm_topic_key(s: str) -> str:
    s = s or ""
    s = s.lower()
    s = re.sub(r"[^\w\u0600-\u06FF]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def load_jsonl(path):
    if not os.path.exists(path): return []
    out = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line))
            except:
                pass
    return out


def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def get_blogger_service():
    creds = Credentials(
        None,
        refresh_token=REFRESH_TOKEN,
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=["https://www.googleapis.com/auth/blogger"],
    )
    return build("blogger", "v3", credentials=creds, cache_discovery=False)


def get_blog_id(service, blog_url):
    return service.blogs().getByUrl(url=blog_url).execute()["id"]


def recent_titles(limit=TITLE_WINDOW):
    titles = []
    try:
        service = get_blogger_service()
        blog_id = get_blog_id(service, BLOG_URL)
        res = service.posts().list(
            blogId=blog_id,
            fetchBodies=False,
            maxResults=limit,
            orderBy="PUBLISHED",
        ).execute()
        for it in (res.get("items") or []):
            t = (it.get("title", "") or "").strip()
            if t: titles.append(t)
    except Exception:
        pass
    titles += [r.get("title", "")
               for r in load_jsonl(HISTORY_TITLES_FILE)][-limit:]
    return set(titles)


def recent_topics(days=TOPIC_WINDOW_D):
    cutoff = datetime.now(TZ) - timedelta(days=days)
    used = []
    for r in load_jsonl(HISTORY_TOPICS_FILE):
        try:
            t = datetime.fromisoformat(r.get("time"))
            if t >= cutoff: used.append(r.get("topic_key", ""))
        except:
            pass
    return set(used)


def record_publish(title, topic_key):
    append_jsonl(HISTORY_TITLES_FILE, {
        "title": title,
        "time": datetime.now(TZ).isoformat()
    })
    append_jsonl(HISTORY_TOPICS_FILE, {
        "topic_key": topic_key,
        "time": datetime.now(TZ).isoformat()
    })


# -------- منع تكرار الصور من خلال أول <img> في أحدث المنشورات --------
_IMG_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.I)


def _url_for_hash(u: str) -> str:
    u = u or ""
    u = u.split("#", 1)[0]
    u = u.split("?", 1)[0]
    if u.startswith("//"): u = "https:" + u
    if u.startswith("http://"): u = "https://" + u[7:]
    return u


def _img_hash(u: str) -> str:
    return hashlib.sha1((_url_for_hash(u)).encode("utf-8")).hexdigest()[:12]


def recent_image_hashes(limit=60):
    hashes = set()
    try:
        svc = get_blogger_service()
        bid = get_blog_id(svc, BLOG_URL)
        res = svc.posts().list(blogId=bid,
                               fetchBodies=True,
                               maxResults=limit,
                               orderBy="PUBLISHED").execute()
        for it in (res.get("items") or []):
            content = it.get("content", "") or ""
            m = _IMG_RE.search(content)
            if m:
                hashes.add(_img_hash(m.group(1)))
    except Exception:
        pass
    return hashes


# =================== Gemini REST ===================
def _rest_generate(ver: str, model: str, prompt: str):
    if model.startswith("models/"):
        model = model.split("/", 1)[1]
    url = f"{GEMINI_API_ROOT}/{ver}/models/{model}:generateContent?key={GEMINI_API_KEY}"
    body = {
        "contents": [{
            "parts": [{
                "text": prompt
            }]
        }],
        "generationConfig": GEN_CONFIG,
    }
    try:
        r = requests.post(url, json=body, timeout=120)
        data = r.json()
        if r.ok and data.get("candidates"):
            return data["candidates"][0]["content"]["parts"][0]["text"]
        return None
    except Exception:
        return None


@backoff.on_exception(backoff.expo,
                      Exception,
                      base=AI_BACKOFF_BASE,
                      max_tries=AI_MAX_RETRIES)
def ask_gemini(prompt: str) -> str:
    attempts = [
        ("v1beta", "gemini-2.5-flash"),
        ("v1", "gemini-2.5-flash"),
        ("v1beta", "gemini-2.0-flash"),
        ("v1", "gemini-2.0-flash"),
        ("v1beta", "gemini-pro"),
        ("v1", "gemini-pro"),
    ]
    last = None
    for ver, model in attempts:
        txt = _rest_generate(ver, model, prompt)
        if txt:
            return clamp_words_ar(strip_code_fences(txt.strip()), 1000, 1400)
        last = f"{ver}/{model}"
    raise RuntimeError(f"Gemini REST error (last tried {last})")


def build_prompt_ar(topic, kind="general", news_link=None):
    base = """
- اكتب مقالة عربية واضحة للقراء العامين.
- اجعل السطر الأول عنوان H1 بصيغة Markdown يبدأ بـ # ويعبّر بدقة عن موضوع المقال.
- الطول بين 1000 و1400 كلمة.
- بنية: مقدمة موجزة، عناوين فرعية منظمة، أمثلة/شواهد، خاتمة مركّزة.
- لا كود/سكريبت/أقواس ثلاثية.
- أضف قسمًا نهائيًا بعنوان "المراجع" يحوي ≥4 مصادر بروابط Markdown قابلة للنقر.
- لا تُدخل صورًا داخل النص (الصورة تُضاف برمجيًا في الأعلى).
- تجنّب الحشو والتكرار.
""".strip()

    extra = ""
    if kind == "news":
        extra = f"""
- الموضوع مرتبط بترند/خبر حديث: "{topic}".
- اربط التحليل بسياق المنطقة العربية عندما يكون مناسبًا.
- أدرج رابط/روابط المصدر ضمن "المراجع": {news_link or "—"}.
""".strip()

    return f"الموضوع: «{topic}»\n{base}\n{extra}\nأنتج النص النهائي مباشرة."


def ensure_references_clickable(article_md, category, topic, news_link=None):
    text = article_md.strip()
    if "المراجع" not in text:
        text += "\n\n## المراجع\n"
    links = re.findall(r"\[[^\]]+\]\((https?://[^)]+)\)", text)
    needed = max(0, 4 - len(links))
    base_refs = {
        "tech": [
            ("MIT Tech Review", "https://www.technologyreview.com/"),
            ("ACM Digital Library", "https://dl.acm.org/"),
            ("IEEE Spectrum", "https://spectrum.ieee.org/"),
            ("WEF Tech", "https://www.weforum.org/focus/technology/"),
        ],
        "science": [
            ("Nature", "https://www.nature.com/"),
            ("Science", "https://www.science.org/"),
            ("Royal Society", "https://royalsociety.org/"),
            ("UNESCO Science", "https://www.unesco.org/reports/science/"),
        ],
        "social": [
            ("UNDP Publications", "https://www.undp.org/publications"),
            ("OECD Library", "https://www.oecd-ilibrary.org/"),
            ("World Bank Data", "https://data.worldbank.org/"),
            ("Brookings", "https://www.brookings.edu/"),
        ],
        "news": [
            ("Google News", "https://news.google.com/"),
            ("BBC Arabic", "https://www.bbc.com/arabic"),
            ("Reuters MENA", "https://www.reuters.com/world/middle-east/"),
            ("Al Jazeera", "https://www.aljazeera.net/"),
        ],
    }
    extra = []
    if category == "news" and news_link:
        extra.append(("مصدر الخبر", news_link))
    extra += base_refs.get(category, base_refs["science"])
    if needed > 0:
        text += "\n"
        for name, url in extra[:needed]:
            text += f"- [{name}]({url})\n"
    return text


# =================== الصور ===================
def wiki_lead_image(title, lang="ar"):
    s = requests.get(
        f"https://{lang}.wikipedia.org/w/api.php",
        params={
            "action": "query",
            "format": "json",
            "prop": "pageimages",
            "piprop": "original|thumbnail",
            "pithumbsize": "1200",
            "titles": title,
        },
        timeout=20,
    )
    if s.status_code != 200: return None
    pages = s.json().get("query", {}).get("pages", {})
    for _, p in pages.items():
        if "original" in p: return p["original"]["source"]
        if "thumbnail" in p: return p["thumbnail"]["source"]
    return None


def fetch_unsplash(topic):
    if not UNSPLASH_ACCESS_KEY: return None
    try:
        r = requests.get(
            "https://api.unsplash.com/search/photos",
            headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
            params={
                "query": topic,
                "per_page": 10,
                "orientation": "landscape"
            },
            timeout=30,
        )
        if not r.ok: return None
        results = (r.json().get("results") or [])
        if not results: return None
        p = random.choice(results)
        url = (p.get("urls") or {}).get("regular") or (p.get("urls")
                                                       or {}).get("full")
        if not url: return None
        user = p.get("user") or {}
        credit = (
            f'صورة من Unsplash — <a href="{html.escape(user.get("links",{}).get("html","https://unsplash.com"))}" '
            f'target="_blank" rel="noopener">{html.escape(user.get("name","Unsplash"))}</a>'
        )
        return {"url": url, "credit": credit}
    except Exception:
        return None


def fetch_image_general(topic):
    for lang in ("ar", "en"):
        try:
            url = wiki_lead_image(topic, lang=lang)
            if url:
                return {"url": url, "credit": f"Image via Wikipedia ({lang})"}
        except Exception:
            pass
    return None


def fetch_pexels(topic):
    if not PEXELS_API_KEY: return None
    try:
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_API_KEY},
            params={
                "query": topic,
                "per_page": 10,
                "orientation": "landscape"
            },
            timeout=30,
        )
        photos = r.json().get("photos", [])
        if photos:
            p = random.choice(photos)
            url = p["src"]["large2x"]
            credit = f'صورة من Pexels — <a href="{html.escape(p["url"])}" target="_blank" rel="noopener">المصدر</a>'
            return {"url": url, "credit": credit}
    except Exception:
        return None


def fetch_pixabay(topic):
    if not PIXABAY_API_KEY: return None
    try:
        r = requests.get(
            "https://pixabay.com/api/",
            params={
                "key": PIXABAY_API_KEY,
                "q": topic,
                "image_type": "photo",
                "per_page": 10,
                "safesearch": "true",
                "orientation": "horizontal",
            },
            timeout=30,
        )
        hits = r.json().get("hits", [])
        if hits:
            p = random.choice(hits)
            url = p["largeImageURL"]
            credit = f'صورة من Pixabay — <a href="{html.escape(p["pageURL"])}" target="_blank" rel="noopener">المصدر</a>'
            return {"url": url, "credit": credit}
    except Exception:
        return None


def _ensure_https(url: str) -> str:
    if not url: return url
    if url.startswith("//"): return "https:" + url
    if url.startswith("http://"): return "https://" + url[7:]
    return url


def fetch_image(query):
    if FORCED_IMAGE:
        return {"url": _ensure_https(FORCED_IMAGE), "credit": "Featured image"}

    topic = (query
             or "Research").split("،")[0].split(":")[0].strip() or "Research"
    used_hashes = recent_image_hashes(limit=60)

    candidates = []

    g = fetch_image_general(topic)
    if g: candidates.append(g)

    for fn in (fetch_pexels, fetch_pixabay, fetch_unsplash):
        img = fn(topic)
        if img: candidates.append(img)

    seed = hashlib.sha1((topic + datetime.now(TZ).strftime("%Y%m%d%H") +
                         str(random.random())).encode("utf-8")).hexdigest()[:8]
    free_candidates = [
        {
            "url":
            f"https://source.unsplash.com/1200x630/?{requests.utils.quote(topic)}&sig={seed}",
            "credit": "Free image source"
        },
        {
            "url":
            f"https://loremflickr.com/1200/630/{requests.utils.quote(topic)}?lock={seed}",
            "credit": "Free image source"
        },
        {
            "url": f"https://picsum.photos/seed/{seed}/1200/630",
            "credit": "Free image source"
        },
    ]
    candidates.extend(free_candidates)

    for c in candidates:
        u = _ensure_https(c.get("url", ""))
        if not u: continue
        h = _img_hash(u)
        if h not in used_hashes:
            return {"url": u, "credit": c.get("credit", "")}

    return {
        "url": "https://via.placeholder.com/1200x630.png?text=LoadingAPK",
        "credit": "Placeholder"
    }


_BAD_SRC_RE = re.compile(
    r'(?:المصدر|source)\s*[:\-–]?\s*(pexels|pixabay|unsplash)', re.I)


def build_post_html(title, img, article_md):
    cover = _ensure_https((img or {}).get("url", "")) if img else ""
    if not cover or not cover.startswith("https://"):
        cover = "https://via.placeholder.com/1200x630.png?text=LoadingAPK"
    img_html = f"""
<figure class="post-cover" style="margin:0 0 12px 0;">
  <img src="{html.escape(cover)}" alt="{html.escape(title)}"
       width="1200" height="675" loading="lazy" decoding="async"
       style="max-width:100%;height:auto;border-radius:8px;display:block;margin:auto;" />
</figure>
<p style="font-size:0.9em;color:#555;margin:4px 0 16px 0;">{(img or {}).get("credit","")}</p>
<hr/>
""".strip() + "\n"
    body_html = markdown_to_clean_html(linkify_urls_md(article_md))
    body_html = _BAD_SRC_RE.sub("", body_html)
    return img_html + body_html


# =================== Google Trends + Google News ===================
def fetch_trends_list(geo: str, max_items=10):
    url = f"https://trends.google.com/trends/trendingsearches/daily/rss?geo={geo}"
    feed = feedparser.parse(url)
    out = []
    for e in feed.entries[:max_items]:
        t = e.title
        link = f"https://www.google.com/search?q={requests.utils.quote(t)}"
        out.append((t, link))
    return out


def fetch_trends_region(geos, per_geo=10):
    bucket = {}
    for geo in geos:
        items = fetch_trends_list(geo, max_items=per_geo)
        for title, link in items:
            k = norm_topic_key(title)
            if not k: continue
            bucket.setdefault(k, {"count": 0, "title": title, "link": link})
            bucket[k]["count"] += 1
    ranked = sorted(bucket.values(), key=lambda x: (-x["count"], x["title"]))
    return [(r["title"], r["link"]) for r in ranked]


def fetch_top_me_news(n=0):
    url = "https://news.google.com/rss?hl=ar&gl=IQ&ceid=IQ:ar"
    feed = feedparser.parse(url)
    if feed.entries:
        idx = min(n, len(feed.entries) - 1)
        e = feed.entries[idx]
        return e.title, e.link
    return None, None


# =================== Blogger API + منطق التحديث/الإنشاء ===================
def _norm_title(s: str) -> str:
    s = (s or "").strip().lower()
    return re.sub(r"\s+", " ", s)


def _fingerprint(title: str, html_content: str) -> str:
    snippet = re.sub(r"<[^>]+>", " ", html_content or "")
    snippet = re.sub(r"\s+", " ", snippet).strip()[:100]
    return hashlib.sha1(
        (_norm_title(title) + "|" + snippet).encode("utf-8")).hexdigest()


def _find_existing_post_by_title(service, blog_id, title):
    norm = _norm_title(title)
    # live
    try:
        resp = service.posts().list(blogId=blog_id,
                                    fetchBodies=False,
                                    maxResults=50,
                                    orderBy="UPDATED",
                                    status=["live"]).execute()
        for it in (resp.get("items") or []):
            if _norm_title(it.get("title")) == norm: return it["id"]
    except Exception:
        pass
    # drafts
    try:
        resp = service.posts().list(blogId=blog_id,
                                    fetchBodies=False,
                                    maxResults=50,
                                    orderBy="UPDATED",
                                    status=["draft"]).execute()
        for it in (resp.get("items") or []):
            if _norm_title(it.get("title")) == norm: return it["id"]
    except Exception:
        pass
    return None


def post_to_blogger(title, html_content, labels=None):
    service = get_blogger_service()
    blog_id = get_blog_id(service, BLOG_URL)
    is_draft = (PUBLISH_MODE != "live")
    body = {"kind": "blogger#post", "title": title, "content": html_content}
    if labels: body["labels"] = labels[:]

    existing_id = _find_existing_post_by_title(service, blog_id, title)
    if existing_id:
        if UPDATE_IF_TITLE_EXISTS:
            upd = service.posts().update(blogId=blog_id,
                                         postId=existing_id,
                                         body=body).execute()
            print("UPDATED:", upd.get("url", upd.get("id")))
            return upd
        # أنشئ جديدًا بعنوان مميّز
        body[
            "title"] = f"{title} — {datetime.now(TZ).strftime('%Y/%m/%d %H:%M')}"
        ins = service.posts().insert(blogId=blog_id,
                                     body=body,
                                     isDraft=is_draft).execute()
        print("CREATED (unique):", ins.get("url", ins.get("id")))
        return ins

    ins = service.posts().insert(blogId=blog_id, body=body,
                                 isDraft=is_draft).execute()
    print("CREATED:", ins.get("url", ins.get("id")))
    return ins


# =================== اختيار الفئة الدورية ===================
def current_cycle_index(today=None):
    d = today or date.today()
    anchor = date(2025, 1, 1)
    return ((d - anchor).days) % 3


def slot_category_for_today(slot_idx, today=None):
    c = current_cycle_index(today)
    if c == 0: return "tech" if slot_idx == 0 else "science"
    if c == 1: return "social" if slot_idx == 0 else "tech"
    return "news" if slot_idx == 0 else "social"


def labels_for_category(category):
    if category == "tech": return ["تكنولوجيا", "ابتكار", "رقمنة"]
    if category == "science": return ["علوم", "بحث علمي"]
    if category == "social": return ["اجتماع", "تنمية", "سياسات"]
    if category == "news": return ["أخبار", "ترند"]
    return ["بحث"]


# =================== توليد موضوع ومقال ===================
def choose_topic_for_category(category, slot_idx):
    rnd = random.Random(f"{date.today().isoformat()}-{category}-{slot_idx}")

    if category == "tech":
        return rnd.choice(TOPICS_TECH)

    if category == "science":
        return rnd.choice(TOPICS_SCIENCE)

    if category == "social":
        return rnd.choice(TOPICS_SOCIAL)

    if category == "news":
        if TREND_GEO_LIST:
            trends = fetch_trends_region(TREND_GEO_LIST, per_geo=10)
        else:
            trends = fetch_trends_list(TREND_GEO, max_items=10)

        if trends:
            idx = 0 if slot_idx == 0 else 1
            if len(trends) > idx:
                return trends[idx]  # (title, link)

        title, link = fetch_top_me_news(n=slot_idx)
        if title:
            return (title, link)

        return ("تطورات مهمة في الشرق الأوسط — قراءة تحليلية",
                "https://news.google.com/")


def build_article_for(category, topic):
    if isinstance(topic, tuple):  # news
        t, lnk = topic
        article = ask_gemini(build_prompt_ar(t, kind="news", news_link=lnk))
        article = ensure_references_clickable(article,
                                              "news",
                                              t,
                                              news_link=lnk)
        title = extract_title(article, t)
        search_query = t
    else:
        t = topic
        article = ask_gemini(build_prompt_ar(t, kind="general"))
        article = ensure_references_clickable(article, category, t)
        title = extract_title(article, t)
        search_query = t
    return title, article, search_query


# ======== أدوات عنوان سليمة (خارج أي دالة أخرى) ========
def _norm_simple(s: str) -> str:
    # تطبيع بسيط للمقارنة: إزالة الرموز وتحويل لحروف صغيرة
    return re.sub(r"[^\w\u0600-\u06FF]+", "", (s or "").strip()).lower()


def extract_title(article_md, fallback_topic):
    """
    يلتقط أول عنوان H1/H2 حقيقي (غير "المراجع/المصادر/الخاتمة/المقدمة"),
    وإن لم يجد، يأخذ أول سطر نصّي معقول. وإلا يعود للموضوع الاحتياطي.
    """
    banned = {
        "المراجع", "المصادر", "references", "sources", "الخاتمة", "خاتمة",
        "المقدمة", "مقدمة"
    }

    # 1) عناوين Markdown (# .. ######)
    for m in re.finditer(r"^\s*#{1,6}\s*(.+?)\s*$", article_md or "", re.M):
        t = (m.group(1) or "").strip()
        x = _norm_simple(t)
        if not x or x in banned or len(t) < 5:
            continue
        return t[:90]

    # 2) أول سطر نصي معقول
    for ln in (article_md or "").splitlines():
        t = (ln or "").strip()
        if not t:
            continue
        if t.startswith("#") or t.startswith(("- ", "* ")):
            continue
        x = _norm_simple(t)
        if x in banned or len(t) < 5:
            continue
        return t[:90]

    # 3) fallback
    return (fallback_topic
            if isinstance(fallback_topic, str) else str(fallback_topic))[:90]


def regenerate_until_unique(category, slot_idx, max_tries=3):
    tried_keys = set()
    used_title_set = recent_titles(TITLE_WINDOW)
    used_topic_keys = recent_topics(TOPIC_WINDOW_D)
    last_title, last_article, last_query = "مقال", "", ""
    for _ in range(max_tries):
        picked = choose_topic_for_category(category, slot_idx)
        topic_key = norm_topic_key(
            picked[0] if isinstance(picked, tuple) else picked)
        if topic_key in used_topic_keys or topic_key in tried_keys:
            tried_keys.add(topic_key)
            continue
        title, article_md, search_query = build_article_for(category, picked)
        last_title, last_article, last_query = title, article_md, search_query
        if title not in used_title_set:
            return title, article_md, search_query, topic_key
        tried_keys.add(topic_key)
    suffix = datetime.now(TZ).strftime(" — %Y/%m/%d %H:%M")
    return f"{last_title}{suffix}", (last_article or "مقال تجريبي"), (
        last_query or "بحث"), norm_topic_key(last_query or "بحث")


# =================== المسار الرئيسي للنشر ===================
def make_article_once(slot_idx):
    cat = slot_category_for_today(slot_idx, date.today())
    title, article_md, search_query, topic_key = regenerate_until_unique(
        cat, slot_idx)
    image = fetch_image(search_query)
    html_content = build_post_html(title, image, article_md)
    labels = labels_for_category(cat)
    result = post_to_blogger(title, html_content, labels=labels)
    record_publish(title, topic_key)
    state = "مسودة" if (PUBLISH_MODE != "live") else "منشور حي"
    print(
        f"[{datetime.now(TZ)}] {state}: {result.get('url','(بدون رابط)')} | {cat} | {title}"
    )


# =================== Webhook (اختياري) ===================
@app.get("/")
def health():
    return "OK", 200


@app.get("/trigger")
def trigger():
    token = request.args.get("token", "")
    slot = request.args.get("slot", "0")
    if TRIGGER_TOKEN and token != TRIGGER_TOKEN:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    try:
        i = int(slot)
        if i not in (0, 1):
            return jsonify({"ok": False, "error": "slot must be 0 or 1"}), 400
        make_article_once(i)
        return jsonify({"ok": True, "slot": i}), 200
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# =================== الجدولة الداخلية ===================
def schedule_jobs():
    sched = BackgroundScheduler(timezone=TZ)
    for idx, t in enumerate(POST_TIMES_LOCAL):
        hour, minute = map(int, t.split(":"))
        sched.add_job(lambda i=idx: make_article_once(i),
                      "cron",
                      hour=hour,
                      minute=minute,
                      id=f"post_{t}")
    sched.start()
    print(
        f"الجدولة فعّالة: {POST_TIMES_LOCAL} بتوقيت بغداد. وضع النشر: {PUBLISH_MODE.upper()}"
    )


# =================== التشغيل ===================
if __name__ == "__main__":
    if USE_EXTERNAL_CRON:
        port = int(os.getenv("PORT", "8000"))
        print(
            f"External-cron mode ON. Webhook: /trigger?slot=0|1&token=***  Port={port}"
        )
        app.run(host="0.0.0.0", port=port)
    else:
        if RUN_ONCE:
            make_article_once(0)
            make_article_once(1)
        else:
            schedule_jobs()
            try:
                while True:
                    time.sleep(30)
            except KeyboardInterrupt:
                pass
