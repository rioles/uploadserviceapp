import os
import sys
import django

# 1. Configurer l'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'videostream.settings.dev')
django.setup()

# 2. Importer les modèles après l'initialisation de Django
from videos.models import Video, VideoChunk

def test_merge_video(video_id_str):
    print(f"🚀 Début du test de fusion pour la vidéo : {video_id_str}")
    
    # Récupérer les video_chunks ordonnés par leur index
    v_chunks = VideoChunk.objects.filter(video_id=video_id_str).order_by('chunk_index')
    
    if not v_chunks.exists():
        print("❌ Aucun chunk trouvé pour cet ID de vidéo.")
        return

    print(f"📦 {v_chunks.count()} chunks trouvés dans la base de données.")
    
    output_path = "/tmp/output_test.mp4"
    
    try:
        with open(output_path, 'wb') as outfile:
            for vc in v_chunks:
                chunk_file_path = vc.chunk.s3_key
                print(f" └─ Lecture du Chunk #{vc.chunk_index} : {chunk_file_path}")
                
                if not os.path.exists(chunk_file_path):
                    print(f"💥 ERREUR : Le fichier physique {chunk_file_path} est introuvable !")
                    return
                
                with open(chunk_file_path, 'rb') as infile:
                    outfile.write(infile.read())
                    
        # --- AJUSTEMENT D'INDENTATION ICI ---
        # Sorti de la boucle 'for' pour ne l'afficher qu'une seule fois à la toute fin
        print(f"🎉 Fusion terminée avec succès ! Fichier généré : {output_path}")
        print(f"⚖️  Taille totale du fichier : {os.path.getsize(output_path)} octets.")

    except Exception as e:
        print(f"❌ Une erreur est survenue durant la fusion : {str(e)}")

if __name__ == "__main__":
    target_video_id = "01966b3a-0000-7000-0000-000000000001"
    test_merge_video(target_video_id)
