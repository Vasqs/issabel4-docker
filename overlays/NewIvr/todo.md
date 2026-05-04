# NewIvr TODO

## Tabelas ausentes / contrato de banco

- [ ] Definir a source of truth da feature `classificacao` no ambiente atual.
  Hoje `report/classificacao_list.php` aponta corretamente para o banco local, mas a validação no `issabel-dev` falhou com `asteriskcdrdb.classificacao` inexistente.
- [ ] Mapear todas as tabelas legadas ainda esperadas pelas views admin e confirmar quais existem no Issabel atual.
  Prioridade: `classificacao`, `URA1`, `queue` com campos customizados usados pelo fluxo URA, e qualquer resquício do banco `IvrCrivel`.
- [ ] Decidir se as features legadas de URA/áudio devem migrar para `call_center`/`asteriskcdrdb` locais ou se precisam de um banco dedicado provisionado no ambiente.
- [ ] Criar migração/runbook reproduzível para as tabelas faltantes do ambiente local antes de reabilitar as views que hoje dependem do schema externo.

## Hardcodes gritantes

- [ ] Remover hardcodes de ambiente externo em `web_root/NewIvr/dasch/dasch_relatorios/chamadas_realtime.php`.
- [ ] Remover hardcodes de ambiente externo em `web_root/NewIvr/dasch/dasch_relatorios/conf_chamadas_realtime.php`.
- [ ] Remover hardcodes de ambiente externo e dependência explícita de `IvrCrivel` em `web_root/NewIvr/dasch/config_ivr.php`.
- [ ] Corrigir o fluxo `Criar Projeto` baseado em `web_root/NewIvr/dasch/index_ura1.html`, `get_audio.php` e `creatprojetodiscfront.php`, hoje preso a `84.247.129.202` / `Marco` / `IvrCrivel`.
- [ ] Corrigir a feature de WhatsApp do menu admin.
  Hoje o menu aponta para `whatssconfig.html`, mas o tree ativo só tem backends hardcoded como `web_root/NewIvr/dasch/dasch_prod/whatssconfig_api.php`.
- [ ] Revisar outros endpoints ativos do menu admin ainda fora do hardening principal.
  Prioridade: `report/grafico/*`, `dasch/*` de agentes/ramais, e páginas de áudio/import antigas ainda não migradas.

## Pontos técnicos em aberto

- [ ] Fazer `web_root/NewIvr/includes/keycloak_guard.php` falhar rápido para ambiente incompleto, em vez de depender de fallbacks hardcoded de issuer, client secret e credenciais locais.
- [ ] Definir provisionamento explícito de `NEWIVR_WEBPHONE_SECRET` no runtime atual.
  Hoje o helper central resolve `secret=''` e a rota local de webphone depende disso para funcionar.
- [ ] Eliminar a exposição do segredo do webphone ao navegador em `web_root/NewIvr/dasch/webphone_launch.php`.
  O segredo saiu do JS, mas ainda é enviado ao cliente via HTML hidden form.
- [ ] Revisar warnings de timezone restantes no PHP legado e padronizar `date_default_timezone_set` nas views/endpoints que ainda emitem ruído no runtime.
- [ ] Confirmar se a sessão/identidade usada no teste de URA deve vir sempre da extensão do usuário autenticado ou se precisa de override por configuração de ambiente.

## Validação pendente

- [ ] Validar em browser autenticado as views já corrigidas para garantir que agora falham pelo motivo certo no ambiente atual, sem fallback silencioso para o banco externo.
- [ ] Depois que as tabelas faltantes forem provisionadas, revalidar `classificacao` end-to-end no container.
- [ ] Depois do hardening do bloco realtime, revalidar `campanha_comp`, `chamadas_realtime` e `conf_chamadas_realtime` no `issabel-dev`.
