

-- 1. Create Database if not exists
CREATE DATABASE IF NOT EXISTS `online_shopping_cart` 
DEFAULT CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE `online_shopping_cart`;

DROP TABLE IF EXISTS `order_items`;
DROP TABLE IF EXISTS `orders`;
DROP TABLE IF EXISTS `cart`;
DROP TABLE IF EXISTS `products`;

CREATE TABLE `products` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `name` VARCHAR(255) NOT NULL,
    `description` TEXT,
    `price` DECIMAL(10, 2) NOT NULL,
    `image` VARCHAR(500) NOT NULL,
    `stock` INT NOT NULL DEFAULT 0,
    `category` VARCHAR(100) NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `cart` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `session_id` VARCHAR(100) NOT NULL,
    `product_id` INT NOT NULL,
    `quantity` INT NOT NULL DEFAULT 1,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT `fk_cart_product` 
        FOREIGN KEY (`product_id`) 
        REFERENCES `products` (`id`) 
        ON DELETE CASCADE,
    INDEX `idx_cart_session` (`session_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;



CREATE TABLE `orders` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `customer_name` VARCHAR(150) NOT NULL,
    `email` VARCHAR(150) NOT NULL,
    `phone` VARCHAR(30) NOT NULL,
    `address` TEXT NOT NULL,
    `total_amount` DECIMAL(10, 2) NOT NULL,
    `payment_method` VARCHAR(50) NOT NULL,
    `payment_status` VARCHAR(50) NOT NULL DEFAULT 'Pending',
    `order_status` VARCHAR(50) NOT NULL DEFAULT 'Confirmed',
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;


CREATE TABLE `order_items` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `order_id` INT NOT NULL,
    `product_id` INT NOT NULL,
    `quantity` INT NOT NULL,
    `price` DECIMAL(10, 2) NOT NULL,
    CONSTRAINT `fk_order_items_order` 
        FOREIGN KEY (`order_id`) 
        REFERENCES `orders` (`id`) 
        ON DELETE CASCADE,
    CONSTRAINT `fk_order_items_product` 
        FOREIGN KEY (`product_id`) 
        REFERENCES `products` (`id`) 
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `products` (`name`, `description`, `price`, `image`, `stock`, `category`) VALUES
(
    'Aura Wireless Noise-Canceling Headphones', 
    'Premium over-ear acoustic headphones with active noise cancellation, 40-hour battery life, and crystal-clear microphone audio.', 
    149.99, 
    'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=700&auto=format&fit=crop&q=80', 
    25, 
    'Audio'
),
(
    'Chronos Smartwatch Series 7', 
    'Sleek titanium smart fitness watch featuring AMOLED retina display, continuous heart rate tracking, ECG, and 5 ATM water resistance.', 
    199.50, 
    'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=700&auto=format&fit=crop&q=80', 
    18, 
    'Wearables'
),
(
    'Mechanical RGB Pro Keyboard', 
    'Ultra-responsive mechanical gaming keyboard featuring hot-swappable tactile switches, per-key RGB backlighting, and aluminum frame.', 
    89.00, 
    'https://images.unsplash.com/photo-1587829741301-dc798b83add3?w=700&auto=format&fit=crop&q=80', 
    30, 
    'Electronics'
),
(
    'Ergonomic Precision Wireless Mouse', 
    'Ergonomic laser mouse designed for all-day palm comfort, fast hyper-scroll wheel, multi-device Bluetooth pairing, and 4000 DPI sensor.', 
    49.99, 
    'https://images.unsplash.com/photo-1527864550417-7fd91fc51a46?w=700&auto=format&fit=crop&q=80', 
    40, 
    'Electronics'
),
(
    'Ultra-Slim 4K USB-C Monitor 27"', 
    'Stunning 27-inch 4K IPS display featuring HDR400, 99% sRGB color accuracy, 65W USB Type-C power delivery, and ultra-thin bezels.', 
    329.00, 
    'https://images.unsplash.com/photo-1527443224154-c4a3942d3acf?w=700&auto=format&fit=crop&q=80', 
    12, 
    'Electronics'
),
(
    'Luxe Minimalist Water Bottle 750ml', 
    'Double-walled vacuum insulated stainless steel water flask that keeps liquids ice cold for 24 hours or piping hot for 12 hours.', 
    24.99, 
    'https://images.unsplash.com/photo-1602143407151-7111542de6e8?w=700&auto=format&fit=crop&q=80', 
    50, 
    'Accessories'
),
(
    'Studio Pro Condenser Microphone', 
    'Studio broadcast quality USB cardioid condenser microphone with built-in pop filter, shock mount, and zero-latency headphone monitoring.', 
    119.00, 
    'https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=700&auto=format&fit=crop&q=80', 
    15, 
    'Audio'
),
(
    'Urban Commuter Waterproof Backpack', 
    'Rugged weather-resistant everyday backpack with dedicated 16-inch padded laptop compartment, anti-theft zipper, and USB charging pass-through.', 
    69.95, 
    'https://images.unsplash.com/photo-1553062407-98eeb64c6a62?w=700&auto=format&fit=crop&q=80', 
    22, 
    'Accessories'
),
(
    'Smart Ambient LED Desk Lamp', 
    'Modern architectural desk lamp with touch brightness dimmer, customizable color temperatures (2700K-6500K), and integrated wireless phone charger.', 
    45.50, 
    'https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=700&auto=format&fit=crop&q=80', 
    28, 
    'Home'
),
(
    'True Wireless Hi-Fi Earbuds', 
    'Compact in-ear wireless earphones with deep bass response, dual noise cancellation microphones, IPX7 sweatproof rating, and wireless charging case.', 
    79.99, 
    'https://images.unsplash.com/photo-1590658268037-6bf12165a8df?w=700&auto=format&fit=crop&q=80', 
    35, 
    'Audio'
),
(
    'Vintage Leather Minimalist Wallet', 
    'Full-grain genuine vintage leather cardholder featuring RFID blocking shields, quick-access card ejection slot, and slim front-pocket profile.', 
    29.99, 
    'https://images.unsplash.com/photo-1627123424574-724758594e93?w=700&auto=format&fit=crop&q=80', 
    45, 
    'Accessories'
),
(
    'Smart Home Security Wi-Fi Camera', 
    '1080p full HD indoor smart camera with 360-degree pan & tilt, AI human detection, infrared night vision, and two-way real-time audio.', 
    59.00, 
    'https://images.unsplash.com/photo-1557324232-b8917d3c3dcb?w=700&auto=format&fit=crop&q=80', 
    20, 
    'Home'
);
