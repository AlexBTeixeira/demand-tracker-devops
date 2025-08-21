-- sql/schema.sql

-- Tabela de Usuários
CREATE TABLE IF NOT EXISTS `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(80) NOT NULL,
  `name` varchar(120) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB;

-- Tabela de Demandas
CREATE TABLE IF NOT EXISTS `demands` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `description` text,
  `status` varchar(50) NOT NULL DEFAULT 'Em Fila',
  `priority` int DEFAULT '0',
  `estimated_hours` decimal(10,2) DEFAULT NULL,
  `executed_hours` decimal(10,2) DEFAULT '0.00',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB;

-- Tabela de Anexos
CREATE TABLE IF NOT EXISTS `attachments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `demand_id` int NOT NULL,
  `filename` varchar(255) NOT NULL,
  `filepath` varchar(1024) NOT NULL,
  `uploaded_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `demand_id` (`demand_id`),
  CONSTRAINT `attachments_ibfk_1` FOREIGN KEY (`demand_id`) REFERENCES `demands` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Tabela de Sessões de Trabalho
CREATE TABLE IF NOT EXISTS `work_sessions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `start_time` datetime NOT NULL,
  `end_time` datetime NOT NULL,
  `total_minutes` int NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB;

-- Tabela de Logs de Trabalho (detalhes de cada sessão)
CREATE TABLE IF NOT EXISTS `work_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `work_session_id` int NOT NULL,
  `demand_id` int NOT NULL,
  `minutes_spent` int NOT NULL,
  `description` text,
  `status_changed_to` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `work_session_id` (`work_session_id`),
  KEY `demand_id` (`demand_id`),
  CONSTRAINT `work_logs_ibfk_1` FOREIGN KEY (`work_session_id`) REFERENCES `work_sessions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `work_logs_ibfk_2` FOREIGN KEY (`demand_id`) REFERENCES `demands` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB;

-- Inserir um usuário padrão para login inicial
-- ATENÇÃO: A senha aqui é 'admin'. Em um ambiente de produção, use um método mais seguro para criar o primeiro usuário.
INSERT INTO `users` (username, name, password_hash) VALUES ('admin', 'Administrador', 'admin') ON DUPLICATE KEY UPDATE name='Administrador';