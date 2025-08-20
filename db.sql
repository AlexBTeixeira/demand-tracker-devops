CREATE DATABASE IF NOT EXISTS demand_tracker;
use demand_tracker;

-- Tabela de Usuários (para  login)
CREATE TABLE users (
  `id` int NOT NULL AUTO_INCREMENT,
  `username` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `name` varchar(100) NOT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Tabela de Demandas (Core da aplicação)
CREATE TABLE `demands` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(255) NOT NULL,
  `description` text,
  `status` varchar(50) NOT NULL DEFAULT 'Em Fila', -- 'Em Fila', 'Em Execução', 'Concluída', 'Cancelada'
  `priority` int NOT NULL DEFAULT 0, -- Para ordenação
  `estimated_hours` decimal(10,2) DEFAULT NULL,
  `executed_hours` decimal(10,2) NOT NULL DEFAULT '0.00',
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Tabela de Anexos para as Demandas
CREATE TABLE `attachments` (
  `id` int NOT NULL AUTO_INCREMENT,
  `demand_id` int NOT NULL,
  `filename` varchar(255) NOT NULL,
  `filepath` varchar(512) NOT NULL, -- Caminho relativo à pasta de uploads
  `uploaded_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `demand_id` (`demand_id`),
  CONSTRAINT `attachments_ibfk_1` FOREIGN KEY (`demand_id`) REFERENCES `demands` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Tabela de Sessões de Trabalho (registra o tempo total de cada sessão)
CREATE TABLE `work_sessions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `start_time` datetime NOT NULL,
  `end_time` datetime NOT NULL,
  `total_minutes` int NOT NULL, -- Duração total da sessão em minutos
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Tabela de Logs de Trabalho (detalha o que foi feito em cada sessão, rateado por demanda)
CREATE TABLE `work_logs` (
  `id` int NOT NULL AUTO_INCREMENT,
  `work_session_id` int NOT NULL,
  `demand_id` int NOT NULL,
  `minutes_spent` int NOT NULL,
  `description` text NOT NULL,
  `status_changed_to` varchar(50) DEFAULT NULL, -- Novo status da demanda, se alterado
  PRIMARY KEY (`id`),
  KEY `work_session_id` (`work_session_id`),
  KEY `demand_id` (`demand_id`),
  CONSTRAINT `work_logs_ibfk_1` FOREIGN KEY (`work_session_id`) REFERENCES `work_sessions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `work_logs_ibfk_2` FOREIGN KEY (`demand_id`) REFERENCES `demands` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Inserir um usuário padrão para o primeiro acesso
-- Senha: admin
INSERT INTO `users` (`username`, `password_hash`, `name`) VALUES
('admin@tracker.com', 'pbkdf2:sha256:600000$c1iSExd1J8fQMMw8$289e61a4f009f429189196a58f70068f5610d487f54c9c5b6b80d92e07971d87', 'Admin Freelancer');