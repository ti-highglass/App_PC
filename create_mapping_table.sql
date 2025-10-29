-- Tabela para mapear peças especiais que precisam gerar XMLs adicionais
CREATE TABLE IF NOT EXISTS public.pc_pecas_especiais (
    id SERIAL PRIMARY KEY,
    projeto TEXT NOT NULL,
    peca_origem TEXT NOT NULL,
    peca_adicional TEXT NOT NULL,
    descricao TEXT,
    ativo BOOLEAN DEFAULT TRUE,
    data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inserir os casos mencionados
INSERT INTO public.pc_pecas_especiais (projeto, peca_origem, peca_adicional, descricao) VALUES
('514', 'TSA', 'TSB', 'Projeto 514 TSA deve gerar também TSB'),
('346', 'TSP', 'TSA', 'Projeto 346 TSP deve gerar também TSA'),
('346', 'TSP', 'TSB', 'Projeto 346 TSP deve gerar também TSB');

-- Comentários para documentação
COMMENT ON TABLE public.pc_pecas_especiais IS 'Tabela para mapear peças que precisam gerar XMLs adicionais durante a otimização';
COMMENT ON COLUMN public.pc_pecas_especiais.projeto IS 'Código do projeto';
COMMENT ON COLUMN public.pc_pecas_especiais.peca_origem IS 'Peça que o usuário seleciona para otimizar';
COMMENT ON COLUMN public.pc_pecas_especiais.peca_adicional IS 'Peça adicional que deve ser incluída no XML';
COMMENT ON COLUMN public.pc_pecas_especiais.descricao IS 'Descrição do mapeamento';
COMMENT ON COLUMN public.pc_pecas_especiais.ativo IS 'Se o mapeamento está ativo';