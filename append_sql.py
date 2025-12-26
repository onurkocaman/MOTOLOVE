
import os

def append_sql():
    path = r'c:\Users\HP\OneDrive\Masaüstü\moto\son.sql'
    
    new_sql = """

-- 
-- Table structure for table `comments`
-- 

CREATE TABLE IF NOT EXISTS `comments` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `motorcycle_id` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `content` text NOT NULL,
  `rating` int(11) DEFAULT 5,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  KEY `motorcycle_id` (`motorcycle_id`),
  KEY `user_id` (`user_id`),
  CONSTRAINT `comments_ibfk_1` FOREIGN KEY (`motorcycle_id`) REFERENCES `motorcycles` (`id`) ON DELETE CASCADE,
  CONSTRAINT `comments_ibfk_2` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_turkish_ci;
"""
    
    with open(path, 'a', encoding='utf-8') as f:
        f.write(new_sql)
    print("Successfully appended to son.sql")

if __name__ == "__main__":
    append_sql()
