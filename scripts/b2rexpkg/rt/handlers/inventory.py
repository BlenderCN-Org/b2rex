from .base import Handler
from pyogp.lib.client.inventory import UDP_Inventory
import uuid
from pyogp.lib.base.datatypes import UUID
from pyogp.lib.base.message.message import Message, Block

def sendRezObject(agent, inventory_item, RayStart, RayEnd, FromTaskID = UUID(), BypassRaycast = 1,  RayTargetID = UUID(), RayEndIsIntersection = False, RezSelected = False, RemoveItem = True, ItemFlags = 0, GroupMask = 0, EveryoneMask = 0, NextOwnerMask = 0):
    """ sends a RezObject packet to a region """

    packet = Message('RezObject',
                    Block('AgentData',
                          AgentID = agent.agent_id,
                          SessionID = agent.session_id,
                          GroupID = agent.ActiveGroupID),
                    Block('RezData',
                          FromTaskID = UUID(str(FromTaskID)),
                          BypassRaycast = BypassRaycast,
                          RayStart = RayStart,
                          RayEnd = RayEnd,
                          RayTargetID = UUID(str(RayTargetID)),
                          RayEndIsIntersection = RayEndIsIntersection,
                          RezSelected = RezSelected,
                          RemoveItem = RemoveItem,
                          ItemFlags = ItemFlags,
                          GroupMask = GroupMask,
                          EveryoneMask = EveryoneMask,
                          NextOwnerMask = NextOwnerMask),
                    Block('InventoryData',
                          ItemID = inventory_item.ItemID,
                          FolderID = inventory_item.FolderID,
                          CreatorID = inventory_item.CreatorID,
                          OwnerID = inventory_item.OwnerID,
                          GroupID = inventory_item.GroupID,
                          BaseMask = inventory_item.BaseMask,
                          OwnerMask = inventory_item.OwnerMask,
                          GroupMask = inventory_item.GroupMask,
                          EveryoneMask = inventory_item.EveryoneMask,
                          GroupOwned = inventory_item.GroupOwned,
                          TransactionID = UUID(),
                          Type = inventory_item.Type,
                          InvType = inventory_item.InvType,
                          Flags = inventory_item.Flags,
                          SaleType = inventory_item.SaleType,
                          SalePrice = inventory_item.SalePrice,
                          Name = inventory_item.Name,
                          Description = inventory_item.Description,
                          CreationDate = inventory_item.CreationDate,
                          CRC = inventory_item.CRC,
                          NextOwnerMask = inventory_item.NextOwnerMask))

    agent.region.enqueue_message(packet)
class InventoryHandler(Handler):
    def onAgentConnected(self, agent):
        self.inventory = UDP_Inventory(agent)

    def onRegionConnect(self, region):
        res = region.message_handler.register("InventoryDescendents")
        res.subscribe(self.onInventoryDescendents)
        self.inventory.enable_callbacks()

    def onRegionConnected(self, region):
        client = self.manager.client

        # send inventory skeleton
        if hasattr(client, 'login_response') and 'inventory-skeleton' in client.login_response:
            self.out_queue.put(["InventorySkeleton",  client.login_response['inventory-skeleton']])

        self.inventory._parse_folders_from_login_response()

    def processFetchInventoryDescendents(self, *args):
        self.logger.debug('inventory processFetchInventoryDescendents')
        self.inventory.sendFetchInventoryDescendentsRequest(*args)

    def processRezObject(self, item_id, raystart, rayend):
        self.logger.debug('inventory processRezObject')
        items = [_item for _item in self.inventory.items if str(_item.ItemID) == item_id]

        if len(items):
            item = items[0]
        else:
            return

        self.logger.debug('sendRezObject', self.manager.client, item, raystart, rayend)
        
        sendRezObject(self.manager.client, item, raystart, rayend)

    def onInventoryDescendents(self, packet):
        logger = self.logger
        logger.debug('onInventoryDescendents')
        folder_id = packet['AgentData'][0]['FolderID']
        folders = [{'Name' : member.Name, 'ParentID' : str(member.ParentID), 'FolderID' : str(member.FolderID)} for member in self.inventory.folders if str(member.ParentID) == str(folder_id)]
        folder = [{'Name' : member.Name, 'ParentID' : str(member.ParentID), 'FolderID' : str(member.FolderID), 'Descendents' : packet['AgentData'][0]['Descendents']} for member in self.inventory.folders if str(member.FolderID) == str(folder_id)]
        folder = folder[0]
        folders.append(folder)
        # return # needs update on pyogp
        items =  [{'Name' : member.Name, 'FolderID' : str(member.FolderID), 'ItemID' : str(member.ItemID), 'InvType' : member.InvType} for member in self.inventory.items if str(member.FolderID) == str(folder_id)] 

        logger.debug("Packet", packet)
        logger.debug("Items", self.inventory.items, "Folders", self.inventory.folders)

        self.out_queue.put(['InventoryDescendents', str(folder_id), folders, items])


