import numpy as np
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from django.core.management.base import BaseCommand
from apis.models import CasheBooking, Trip, Driver  # تأكد من أن نموذج Driver موجود

class Command(BaseCommand):
    help = 'يطبق DBSCAN على حجوزات الكاش PENDING لتجميعها مكانيًا ومن ثم إنشاء رحلة لكل عنقود مع تعيين قيم افتراضية للبيانات غير المتوفرة'

    def add_arguments(self, parser):
        parser.add_argument(
            '--eps', type=float, default=0.5,
            help='المسافة القصوى للنقاط لتكون ضمن نفس العنقود في DBSCAN'
        )
        parser.add_argument(
            '--min_samples', type=int, default=5,
            help='عدد العينات الدنيا لتشكيل عنقود في DBSCAN'
        )

    def handle(self, *args, **options):
        eps = options['eps']
        min_samples = options['min_samples']

        # جلب الحجوزات ذات الحالة PENDING
        bookings = CasheBooking.objects.filter(status=CasheBooking.Status.PENDING)
        total = bookings.count()
        if total == 0:
            self.stdout.write(self.style.WARNING('لا توجد حجوزات PENDING.'))
            return

        self.stdout.write(f'جارٍ تحليل {total} حجز PENDING…')

        # تجهيز بيانات الإحداثيات
        coords = []
        valid_bookings = []
        for b in bookings:
            try:
                lat1, lon1 = map(float, b.from_location.split(','))
                lat2, lon2 = map(float, b.to_location.split(','))
                coords.append([lat1, lon1, lat2, lon2])
                valid_bookings.append(b)
            except Exception as e:
                self.stdout.write(self.style.ERROR(
                    f'تخطي الحجز {b.id} (خطأ في الإحداثيات): {e}'
                ))

        if not coords:
            self.stdout.write(self.style.ERROR('لا بيانات صالحة للتحليل.'))
            return

        X = np.array(coords)
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # تطبيق DBSCAN
        clusterer = DBSCAN(eps=eps, min_samples=min_samples)
        labels = clusterer.fit_predict(X_scaled)

        clusters = set(labels)
        # استبعاد الضوضاء (-1)
        n_clusters = len(clusters) - (1 if -1 in clusters else 0)
        noise_count = list(labels).count(-1)

        self.stdout.write(self.style.SUCCESS('\n==== نتائج DBSCAN ====\n'))
        self.stdout.write(f'عناقيد مكتشفة: {n_clusters}')
        self.stdout.write(f'حجوزات ضوضاء: {noise_count} ({noise_count/len(labels)*100:.2f}%)\n')

        # الحصول على سائق افتراضي لإنشاء الرحلات
        default_driver = Driver.objects.first()
        if not default_driver:
            self.stdout.write(self.style.ERROR('لم يتم العثور على سائق افتراضي. الرجاء إنشاء سائق أولاً.'))
            return

        # إنشاء رحلة لكل عنقود (باستثناء الضوضاء) مع تعيين القيم الافتراضية للحقول غير المعادة من الخوارزمية
        for cid in sorted(clusters):
            if cid == -1:
                continue

            indices = [i for i, lbl in enumerate(labels) if lbl == cid]
            self.stdout.write(self.style.MIGRATE_HEADING(
                f'-- عنقود {cid} ({len(indices)} حجوزات) --'
            ))
            sample = valid_bookings[indices[0]]
            self.stdout.write(f'مثال: ID={sample.id}, from={sample.from_location}, to={sample.to_location}, time={sample.departure_time}')

            trip = Trip.objects.create(
                from_location=sample.from_location,
                to_location=sample.to_location,
                departure_time=sample.departure_time,
                estimated_duration=None,       # قيمة افتراضية
                available_seats=0,             # قيمة افتراضية
                distance_km=None,              # قيمة افتراضية
                price_per_seat=None,           # قيمة افتراضية
                driver=default_driver,
                route_coordinates='{}'         # قيمة افتراضية (JSON فارغ)
            )
            self.stdout.write(self.style.SUCCESS(
                f'تم إنشاء الرحلة للعنقود {cid} (عدد الحجوزات: {len(indices)}) - رقم الرحلة: {trip.id}'
            ))

        # عرض أمثلة على بعض الحجوزات التي صنفت كضوضاء (إن وجدت)
        noise_indices = [i for i, lbl in enumerate(labels) if lbl == -1][:5]
        if noise_indices:
            self.stdout.write(self.style.WARNING('\nأمثلة على الحجوزات الضوضاء:'))
            for i in noise_indices:
                b = valid_bookings[i]
                self.stdout.write(f'  - ID={b.id}, from={b.from_location}, to={b.to_location}, time={b.departure_time}')

        self.stdout.write(self.style.SUCCESS('\nانتهى التحليل.'))
