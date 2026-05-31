import mysql.connector
from mysql.connector import Error

# Database connection configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '',
    'database': 'kewajaran'
}

class DataValidator:
    def __init__(self):
        self.connection = None
        self.connect_db()
        
    def connect_db(self):
        """Connect to MySQL database"""
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            if self.connection.is_connected():
                print("Successfully connected to MySQL database")
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            raise
    
    def disconnect_db(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("MySQL connection closed")
    
    def get_table_counts(self):
        """Get record counts for all tables"""
        cursor = self.connection.cursor()
        
        tables = ['pemdas', 'skpds', 'nomenklaturs', 'usulan_anggarans', 'realisasi_anggarans', 'users']
        
        print("=" * 50)
        print("DATABASE RECORD COUNTS")
        print("=" * 50)
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"{table:25}: {count:,} records")
            except Error as e:
                print(f"{table:25}: Error - {e}")
        
        cursor.close()
    
    def get_yearly_summary(self):
        """Get yearly data summary"""
        cursor = self.connection.cursor()
        
        print("\n" + "=" * 50)
        print("YEARLY DATA SUMMARY")
        print("=" * 50)
        
        # Usulan anggaran per year
        cursor.execute("""
            SELECT tahun, COUNT(*) as count, SUM(pagu) as total_pagu
            FROM usulan_anggarans 
            GROUP BY tahun 
            ORDER BY tahun
        """)
        
        results = cursor.fetchall()
        print(f"{'Year':<6} {'Records':<10} {'Total Pagu (Rp)':<20}")
        print("-" * 40)
        
        for year, count, total_pagu in results:
            print(f"{year:<6} {count:<10,} {total_pagu:>20,.0f}")
        
        # Realisasi anggaran per year
        cursor.execute("""
            SELECT tahun, COUNT(*) as count, SUM(pagu_realisasi) as total_realisasi
            FROM realisasi_anggarans 
            GROUP BY tahun 
            ORDER BY tahun
        """)
        
        results = cursor.fetchall()
        print(f"\n{'Year':<6} {'Realisasi Records':<18} {'Total Realisasi (Rp)':<20}")
        print("-" * 50)
        
        for year, count, total_realisasi in results:
            print(f"{year:<6} {count:<18,} {total_realisasi:>20,.0f}")
        
        cursor.close()
    
    def get_regional_summary(self):
        """Get regional data summary"""
        cursor = self.connection.cursor()
        
        print("\n" + "=" * 50)
        print("REGIONAL DATA SUMMARY")
        print("=" * 50)
        
        cursor.execute("""
            SELECT p.kodepemda, p.namapemda, p.jenis_pemda, 
                   COUNT(u.id) as usulan_count, 
                   SUM(u.pagu) as total_pagu,
                   COUNT(r.id) as realisasi_count,
                   SUM(r.pagu_realisasi) as total_realisasi
            FROM pemdas p
            LEFT JOIN usulan_anggarans u ON p.kodepemda = u.kodepemda
            LEFT JOIN realisasi_anggarans r ON p.kodepemda = r.kodepemda
            GROUP BY p.kodepemda, p.namapemda, p.jenis_pemda
            ORDER BY p.jenis_pemda, p.namapemda
        """)
        
        results = cursor.fetchall()
        
        print(f"{'Kode':<8} {'Nama Pemda':<25} {'Jenis':<8} {'Usulan':<8} {'Pagu (M)':<12} {'Realisasi':<10} {'Real (M)':<12}")
        print("-" * 85)
        
        for kode, nama, jenis, usulan_count, total_pagu, realisasi_count, total_realisasi in results:
            pagu_m = total_pagu / 1000000 if total_pagu else 0
            real_m = total_realisasi / 1000000 if total_realisasi else 0
            print(f"{kode:<8} {nama:<25} {jenis:<8} {usulan_count:<8,} {pagu_m:>12.1f} {realisasi_count:<10,} {real_m:>12.1f}")
        
        cursor.close()
    
    def get_top_programs(self):
        """Get top programs by budget"""
        cursor = self.connection.cursor()
        
        print("\n" + "=" * 50)
        print("TOP 10 PROGRAMS BY BUDGET (All Years)")
        print("=" * 50)
        
        cursor.execute("""
            SELECT n.uraiprogram, SUM(u.pagu) as total_pagu, COUNT(*) as count
            FROM usulan_anggarans u
            JOIN nomenklaturs n ON u.kodesubkegiatan = n.kodesubkegiatan
            GROUP BY n.uraiprogram
            HAVING total_pagu > 0
            ORDER BY total_pagu DESC
            LIMIT 10
        """)
        
        results = cursor.fetchall()
        
        print(f"{'Program':<50} {'Total Pagu (M)':<15} {'Count':<8}")
        print("-" * 75)
        
        for program, total_pagu, count in results:
            pagu_m = total_pagu / 1000000
            # Truncate long program names
            program_display = program[:47] + "..." if len(program) > 50 else program
            print(f"{program_display:<50} {pagu_m:>15.1f} {count:<8}")
        
        cursor.close()
    
    def check_data_quality(self):
        """Check data quality issues"""
        cursor = self.connection.cursor()
        
        print("\n" + "=" * 50)
        print("DATA QUALITY CHECKS")
        print("=" * 50)
        
        # Check for zero targets
        cursor.execute("SELECT COUNT(*) FROM usulan_anggarans WHERE target = 0")
        zero_target_count = cursor.fetchone()[0]
        print(f"Records with zero target: {zero_target_count:,}")
        
        # Check for zero pagu
        cursor.execute("SELECT COUNT(*) FROM usulan_anggarans WHERE pagu = 0")
        zero_pagu_count = cursor.fetchone()[0]
        print(f"Records with zero pagu: {zero_pagu_count:,}")
        
        # Check for null BSK calculations
        cursor.execute("SELECT COUNT(*) FROM usulan_anggarans WHERE bsk = 0")
        zero_bsk_count = cursor.fetchone()[0]
        print(f"Records with zero BSK: {zero_bsk_count:,}")
        
        # Check for missing realisasi (2024-2025)
        cursor.execute("""
            SELECT u.tahun, COUNT(*) as missing_count
            FROM usulan_anggarans u
            LEFT JOIN realisasi_anggarans r ON u.tahun = r.tahun AND u.kodepemda = r.kodepemda 
                AND u.kodeskpd = r.kodeskpd AND u.kodesubkegiatan = r.kodesubkegiatan
            WHERE u.tahun IN (2024, 2025) AND r.id IS NULL
            GROUP BY u.tahun
        """)
        
        results = cursor.fetchall()
        for year, missing_count in results:
            print(f"Missing realisasi for {year}: {missing_count:,}")
        
        cursor.close()
    
    def run_validation(self):
        """Run all validation checks"""
        self.get_table_counts()
        self.get_yearly_summary()
        self.get_regional_summary()
        self.get_top_programs()
        self.check_data_quality()

def main():
    """Main function"""
    try:
        validator = DataValidator()
        validator.run_validation()
    except Exception as e:
        print(f"Validation error: {e}")
    finally:
        if 'validator' in locals():
            validator.disconnect_db()

if __name__ == "__main__":
    main()
