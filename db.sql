-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Server version:               5.5.27 - MySQL Community Server (GPL)
-- Server OS:                    Win64
-- HeidiSQL version:             7.0.0.4053
-- Date/time:                    2012-08-06 23:47:53
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!40014 SET FOREIGN_KEY_CHECKS=0 */;

-- Dumping database structure for pytest
DROP DATABASE IF EXISTS `pytest`;
CREATE DATABASE IF NOT EXISTS `pytest` /*!40100 DEFAULT CHARACTER SET utf8 */;
USE `pytest`;


-- Dumping structure for table pytest.boards
DROP TABLE IF EXISTS `boards`;
CREATE TABLE IF NOT EXISTS `boards` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `name` varchar(10) NOT NULL,
  `title` varchar(50) NOT NULL,
  `desc` varchar(500) NOT NULL,
  `default_name` varchar(100) NOT NULL DEFAULT 'Anonymous',
  `force_default` tinyint(3) unsigned NOT NULL,
  `locked` tinyint(3) unsigned NOT NULL,
  `max_threads` int(10) unsigned NOT NULL DEFAULT '150',
  `threads_per_page` int(10) unsigned NOT NULL DEFAULT '15',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Data exporting was unselected.


-- Dumping structure for table pytest.posts
DROP TABLE IF EXISTS `posts`;
CREATE TABLE IF NOT EXISTS `posts` (
  `id` int(10) unsigned NOT NULL AUTO_INCREMENT,
  `board_id` int(10) unsigned NOT NULL DEFAULT '0',
  `parent_id` int(10) unsigned NOT NULL DEFAULT '0',
  `subject` varchar(200) DEFAULT NULL,
  `name` varchar(100) DEFAULT NULL,
  `message` text,
  `date` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `bumped` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00' COMMENT 'a frissítéskor ezt ÉS a parent-ot is frissíteni kell',
  `stickied` tinyint(3) unsigned NOT NULL DEFAULT '0',
  `locked` tinyint(3) unsigned NOT NULL DEFAULT '0',
  PRIMARY KEY (`id`,`board_id`),
  KEY `parent_id` (`parent_id`),
  KEY `bumped` (`bumped`),
  KEY `FK_posts_boards` (`board_id`),
  CONSTRAINT `FK_posts_boards` FOREIGN KEY (`board_id`) REFERENCES `boards` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- Data exporting was unselected.
/*!40014 SET FOREIGN_KEY_CHECKS=1 */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
