import pandas as pd
import streamlit as st
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime

# Conectar ao banco de dados
def get_db_connection():
    uri = "mongodb+srv://nsnunes01:1pNO2JJzZTotwsmB@cluster0.tqvnk7i.mongodb.net/"
    client = MongoClient(uri)
    db = client['lista_futebol']
    return db

db = get_db_connection()

# Funções auxiliares para banco de dados
def cadastrar_jogador(nome, contato, tipo):
    db.jogadores.insert_one({"nome": nome, "contato": contato, "tipo": tipo})

def criar_partida(data, local, vagas_linha, vagas_goleiro, valor):
    data_str = data.strftime("%Y-%m-%d")
    
    db.partidas.insert_one({
        "data": data_str,
        "local": local,
        "vagas_linha": vagas_linha,
        "vagas_goleiro": vagas_goleiro,
        "valor": valor,
        "confirmados_linha": 0,
        "confirmados_goleiro": 0,
        "jogadores": [],
        "createdAt": datetime.now(),
        "updatedAt": datetime.now()
    })

def atualizar_jogador(partida_id, jogador_id, status=None, pagamento=None):
    filtro = {"_id": ObjectId(partida_id), "jogadores.jogador_id": ObjectId(jogador_id)}
    atualizacao = {}
    if status:
        atualizacao["jogadores.$.status"] = status
    if pagamento:
        atualizacao["jogadores.$.pagamento"] = pagamento

    db.partidas.update_one(filtro, {"$set": atualizacao, "updatedAt": datetime.now()})

def confirmar_presenca(jogador_id, partida_id, tipo):
    # Verificar se o jogador já está confirmado na partida
    partida = db.partidas.find_one({"_id": ObjectId(partida_id), "jogadores.jogador_id": ObjectId(jogador_id)})
    if partida:
        st.warning("O jogador já está confirmado nesta partida.")
        return

    jogador = db.jogadores.find_one({"_id": ObjectId(jogador_id)})
    partida = db.partidas.find_one({"_id": ObjectId(partida_id)})
    
    jogador_info = {
        "jogador_id": jogador_id,
        "nome": jogador["nome"],
        "tipo": tipo,
        "status": "confirmado" if (tipo == "linha" and partida["confirmados_linha"] < partida["vagas_linha"]) or (tipo == "goleiro" and partida["confirmados_goleiro"] < partida["vagas_goleiro"]) else "espera",
        "pagamento": "pendente" if tipo == "linha" else "isento"
    }

    # Atualizar contagem de confirmados
    if jogador_info["status"] == "confirmado":
        if tipo == "linha":
            db.partidas.update_one({"_id": ObjectId(partida_id)}, {"$inc": {"confirmados_linha": 1}})
        else:
            db.partidas.update_one({"_id": ObjectId(partida_id)}, {"$inc": {"confirmados_goleiro": 1}})
    
    db.partidas.update_one({"_id": ObjectId(partida_id)}, {"$push": {"jogadores": jogador_info}, "$set": {"updatedAt": datetime.now()}})
    st.success(f"Presença confirmada como {tipo}, pagamento {'pendente' if tipo == 'linha' else 'isento'}!")

def listar_partidas():
    return list(db.partidas.find())

def listar_jogadores():
    return list(db.jogadores.find())

# Interface do Streamlit
st.title("Lista de Presença para Futebol entre Amigos")

menu = ["Cadastrar Jogador", "Criar Partida", "Confirmar Presença", "Visualizar Partidas"]
escolha = st.sidebar.selectbox("Menu", menu)

# Cadastrar Jogador
if escolha == "Cadastrar Jogador":
    st.subheader("Cadastro de Jogador")
    nome = st.text_input("Nome")
    contato = st.text_input("Contato")
    tipo = st.radio("Tipo de Jogador", ["linha", "goleiro", "ambos"])
    if st.button("Cadastrar"):
        cadastrar_jogador(nome, contato, tipo)
        st.success(f"Jogador {nome} cadastrado como {tipo} com sucesso!")

# Criar Partida
elif escolha == "Criar Partida":
    st.subheader("Criar Nova Partida")
    data = st.date_input("Data")
    local = st.text_input("Local")
    vagas_linha = st.number_input("Vagas para Jogadores de Linha", min_value=1)
    vagas_goleiro = st.number_input("Vagas para Goleiros", min_value=1)
    valor = st.number_input("Valor por Jogador de Linha", min_value=0.0)
    if st.button("Criar Partida"):
        criar_partida(data, local, vagas_linha, vagas_goleiro, valor)
        st.success(f"Partida criada para {data} no {local}!")

# Confirmar Presença
elif escolha == "Confirmar Presença":
    st.subheader("Confirmar Presença em Partida")
    jogadores = listar_jogadores()
    partidas = listar_partidas()

    if not jogadores:
        st.warning("Nenhum jogador cadastrado. Por favor, cadastre um jogador primeiro.")
    else:
        jogador_id = st.selectbox("Selecione o Jogador", [jog["_id"] for jog in jogadores], format_func=lambda x: next(jog["nome"] for jog in jogadores if jog["_id"] == x))
        tipo_jogador = next(jog["tipo"] for jog in jogadores if jog["_id"] == jogador_id)
        partida_id = st.selectbox("Selecione a Partida", [part["_id"] for part in partidas], format_func=lambda x: next(f"{part['data']} - {part['local']}" for part in partidas if part["_id"] == x))

        if tipo_jogador == "ambos":
            tipo = st.radio("Escolha a Posição", ["linha", "goleiro"])
        else:
            tipo = tipo_jogador

        if st.button("Confirmar"):
            confirmar_presenca(jogador_id, partida_id, tipo)

# Visualizar Partidas e Presenças
elif escolha == "Visualizar Partidas":
    st.subheader("Partidas Criadas")
    partidas = listar_partidas()

    if not partidas:
        st.info("Nenhuma partida criada ainda.")
    else:
        for partida in partidas:
            st.markdown(f"### Partida: {partida['data']} - {partida['local']}")
            st.markdown(f"**Linhas Confirmadas:** {partida['confirmados_linha']}/{partida['vagas_linha']}, **Goleiros Confirmados:** {partida['confirmados_goleiro']}/{partida['vagas_goleiro']}")

            if "jogadores" in partida:
                data = []
                for jogador in partida["jogadores"]:
                    nome = jogador.get("nome", "")
                    tipo = jogador.get("tipo", "")
                    status = jogador.get("status", "")
                    pagamento = jogador.get("pagamento", "")
                    data.append([nome, tipo, status, pagamento])

                df_presencas = pd.DataFrame(data, columns=["Nome", "Tipo", "Status", "Pagamento"])
                st.table(df_presencas)

                for jogador in partida["jogadores"]:
                    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
                    with col1:
                        if st.button(f"Remover {jogador['nome']}", key=f"remove_{jogador['jogador_id']}"):
                            atualizar_jogador(partida["_id"], jogador["jogador_id"], status="removido")
                            st.success(f"Jogador {jogador['nome']} removido com sucesso.")
                    with col2:
                        if st.button(f"Espera {jogador['nome']}", key=f"espera_{jogador['jogador_id']}"):
                            atualizar_jogador(partida["_id"], jogador["jogador_id"], status="espera")
                            st.success(f"Jogador {jogador['nome']} colocado em espera.")
                    with col3:
                        if st.button(f"Pago {jogador['nome']}", key=f"pago_{jogador['jogador_id']}"):
                            atualizar_jogador(partida["_id"], jogador["jogador_id"], pagamento="pago")
                            st.success(f"Pagamento de {jogador['nome']} confirmado.")
                    with col4:
                        if st.button(f"Pendente {jogador['nome']}", key=f"pendente_{jogador['jogador_id']}"):
                            atualizar_jogador(partida["_id"], jogador["jogador_id"], pagamento="pendente")
                            st.success(f"Pagamento de {jogador['nome']} alterado para pendente.")
            else:
                st.info("Nenhuma presença confirmada para esta partida.")
