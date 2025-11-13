import { useState, useEffect } from 'react'
import Button from '@/components/ui/Button'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/Dialog'
import Input from '@/components/ui/Input'
import { useGraphStore } from '@/stores/graph'
import { toast } from 'sonner'
import { Trash2Icon, AlertCircleIcon, MergeIcon } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { mergeEntities, deleteEntity, isUserAdmin } from '@/api/lightrag'

export default function GraphActions() {
  const { t } = useTranslation()
  const [showDeleteDialog, setShowDeleteDialog] = useState(false)
  const [showMergeDialog, setShowMergeDialog] = useState(false)
  const [showPermanentDeleteDialog, setShowPermanentDeleteDialog] = useState(false)
  const [targetEntityName, setTargetEntityName] = useState('')
  const [isMerging, setIsMerging] = useState(false)
  const [isDeleting, setIsDeleting] = useState(false)
  const [userIsAdmin, setUserIsAdmin] = useState(false)
  
  const selectedNodes = useGraphStore.use.selectedNodes()
  const selectedEdges = useGraphStore.use.selectedEdges()
  const sigmaGraph = useGraphStore.use.sigmaGraph()
  const rawGraph = useGraphStore.use.rawGraph()
  const clearSelection = useGraphStore.use.clearSelection()
  const setLastSuccessfulQueryLabel = useGraphStore.use.setLastSuccessfulQueryLabel()

  const hasSelection = selectedNodes.size > 0 || selectedEdges.size > 0
  const hasMultipleNodes = selectedNodes.size > 1
  
  useEffect(() => {
    setUserIsAdmin(isUserAdmin())
  }, [])

  const openMergeDialog = () => {
    if (selectedNodes.size < 2) {
      toast.error(t('graphPanel.actions.mergeMinError', 'Sélectionnez au moins 2 nœuds pour fusionner'))
      return
    }
    
    const nodeIds = Array.from(selectedNodes)
    const firstNodeId = nodeIds[0]
    
    if (rawGraph && rawGraph.nodeIdMap[firstNodeId] !== undefined) {
      const firstNode = rawGraph.nodes[rawGraph.nodeIdMap[firstNodeId]]
      const entityName = firstNode.properties?.entity_name || firstNode.properties?.source_id || firstNodeId
      setTargetEntityName(entityName)
    } else {
      setTargetEntityName(firstNodeId)
    }
    
    setShowMergeDialog(true)
  }

  const handleMergeNodes = async () => {
    if (!targetEntityName.trim()) {
      toast.error(t('graphPanel.actions.targetEntityRequired', 'Le nom de l\'entité cible est requis'))
      return
    }

    setIsMerging(true)
    
    try {
      const nodeIds = Array.from(selectedNodes)
      const allNodeNames: string[] = []
      
      nodeIds.forEach(nodeId => {
        if (rawGraph && rawGraph.nodeIdMap[nodeId] !== undefined) {
          const node = rawGraph.nodes[rawGraph.nodeIdMap[nodeId]]
          const entityName = node.properties?.entity_name || node.properties?.source_id || nodeId
          allNodeNames.push(entityName)
        }
      })

      if (allNodeNames.length < 2) {
        toast.error(t('graphPanel.actions.notEnoughNodes', 'Sélectionnez au moins 2 nœuds'))
        setIsMerging(false)
        return
      }

      const sourceNames: string[] = []
      let targetFound = false
      
      for (const name of allNodeNames) {
        if (name === targetEntityName.trim() && !targetFound) {
          targetFound = true
        } else {
          sourceNames.push(name)
        }
      }

      if (sourceNames.length === 0) {
        toast.error(t('graphPanel.actions.noNodesToMerge', 'Aucun nœud à fusionner'))
        setIsMerging(false)
        return
      }

      const result = await mergeEntities(sourceNames, targetEntityName.trim())
      
      toast.success(result.message || 'Fusion réussie', { duration: 4000 })
      
      setLastSuccessfulQueryLabel('')
      
      clearSelection()
      setShowMergeDialog(false)
      setTargetEntityName('')
      
      window.location.reload()
    } catch (error: any) {
      console.error('Error merging nodes:', error)
      const errorMsg = error.response?.data?.detail || error.message || 'Erreur lors de la fusion'
      toast.error(errorMsg)
    } finally {
      setIsMerging(false)
    }
  }

  const handleDeleteSelection = () => {
    if (!sigmaGraph) {
      toast.error(t('graphPanel.actions.deleteError', 'Erreur lors de la suppression'))
      return
    }

    try {
      let deletedCount = 0

      selectedNodes.forEach(nodeId => {
        if (sigmaGraph.hasNode(nodeId)) {
          sigmaGraph.dropNode(nodeId)
          deletedCount++
        }
      })

      selectedEdges.forEach(edgeId => {
        if (sigmaGraph.hasEdge(edgeId)) {
          sigmaGraph.dropEdge(edgeId)
          deletedCount++
        }
      })

      clearSelection()
      setShowDeleteDialog(false)
      
      toast.success(
        t('graphPanel.actions.deleteSuccess', `${deletedCount} éléments masqués de la visualisation`),
        { duration: 4000 }
      )
      toast.info(
        t('graphPanel.actions.temporaryChange', 'Modifications temporaires - rechargez pour restaurer'),
        { duration: 6000 }
      )
    } catch (error) {
      console.error('Error hiding selection:', error)
      toast.error(t('graphPanel.actions.deleteError', 'Erreur lors du masquage'))
    }
  }

  const handlePermanentDelete = async () => {
    if (selectedNodes.size !== 1) {
      toast.error(t('graphPanel.actions.deleteOneNode', 'Sélectionnez un seul nœud pour supprimer'))
      return
    }

    setIsDeleting(true)
    
    try {
      const nodeIds = Array.from(selectedNodes)
      const nodeId = nodeIds[0]
      
      let entityName = nodeId
      if (rawGraph && rawGraph.nodeIdMap[nodeId] !== undefined) {
        const node = rawGraph.nodes[rawGraph.nodeIdMap[nodeId]]
        entityName = node.properties?.entity_name || node.properties?.source_id || nodeId
      }

      const result = await deleteEntity(entityName)
      
      toast.success(result.message || 'Suppression réussie', { duration: 4000 })
      
      setLastSuccessfulQueryLabel('')
      clearSelection()
      setShowPermanentDeleteDialog(false)
      
      window.location.reload()
    } catch (error: any) {
      console.error('Error deleting node:', error)
      const errorMsg = error.response?.data?.detail || error.message || 'Erreur lors de la suppression'
      toast.error(errorMsg)
    } finally {
      setIsDeleting(false)
    }
  }

  if (!hasSelection) return null

  return (
    <>
      <div className="absolute top-20 left-2 flex flex-col gap-2 bg-background/90 p-3 rounded-lg border backdrop-blur-sm max-w-xs">
        <div className="flex items-center gap-2 text-xs text-muted-foreground mb-1">
          <AlertCircleIcon className="w-3 h-3" />
          <span>
            {selectedNodes.size > 0 && `${selectedNodes.size} nœud(s)`}
            {selectedNodes.size > 0 && selectedEdges.size > 0 && ', '}
            {selectedEdges.size > 0 && `${selectedEdges.size} relation(s)`}
          </span>
        </div>
        
        {hasMultipleNodes && userIsAdmin && (
          <Button
            size="sm"
            variant="default"
            onClick={openMergeDialog}
          >
            <MergeIcon className="w-4 h-4 mr-1" />
            {t('graphPanel.actions.merge', 'Fusionner')}
          </Button>
        )}
        
        {selectedNodes.size === 1 && userIsAdmin && (
          <Button
            size="sm"
            variant="destructive"
            onClick={() => setShowPermanentDeleteDialog(true)}
          >
            <Trash2Icon className="w-4 h-4 mr-1" />
            {t('graphPanel.actions.delete', 'Supprimer définitivement')}
          </Button>
        )}
        
        {selectedEdges.size > 0 && (
          <>
            <div className="text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-950/30 p-2 rounded border border-amber-200 dark:border-amber-800">
              <AlertCircleIcon className="w-3 h-3 inline mr-1" />
              {t('graphPanel.actions.temporaryWarning', 'Le masquage est temporaire et sera annulé au rechargement')}
            </div>
            
            <Button
              size="sm"
              variant="destructive"
              onClick={() => setShowDeleteDialog(true)}
            >
              <Trash2Icon className="w-4 h-4 mr-1" />
              {t('graphPanel.actions.hide', 'Masquer')}
            </Button>
          </>
        )}
        
        <Button
          size="sm"
          variant="ghost"
          onClick={clearSelection}
        >
          {t('graphPanel.actions.clearSelection', 'Effacer sélection')}
        </Button>
      </div>

      <Dialog open={showMergeDialog} onOpenChange={setShowMergeDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('graphPanel.actions.mergeTitle', 'Fusionner les nœuds')}</DialogTitle>
            <DialogDescription>
              {t('graphPanel.actions.mergeDescription', 
                `Fusionner ${selectedNodes.size} nœuds en une seule entité. Toutes les relations seront transférées vers l'entité cible.`
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <label htmlFor="target-entity" className="text-sm font-medium">
                {t('graphPanel.actions.targetEntity', 'Nom de l\'entité cible')}
              </label>
              <Input
                id="target-entity"
                value={targetEntityName}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setTargetEntityName(e.target.value)}
                placeholder={t('graphPanel.actions.targetEntityPlaceholder', 'Entrez le nom de l\'entité cible')}
                className="mt-1"
              />
              <p className="text-xs text-muted-foreground mt-1">
                {t('graphPanel.actions.targetEntityHelp', 'Les autres nœuds seront fusionnés dans cette entité')}
              </p>
            </div>
          </div>
          <div className="flex gap-2 justify-end mt-4">
            <Button 
              variant="ghost" 
              onClick={() => {
                setShowMergeDialog(false)
                setTargetEntityName('')
              }}
              disabled={isMerging}
            >
              {t('common.cancel', 'Annuler')}
            </Button>
            <Button 
              variant="default" 
              onClick={handleMergeNodes}
              disabled={isMerging || !targetEntityName.trim()}
            >
              {isMerging ? t('common.loading', 'Chargement...') : t('common.confirm', 'Confirmer')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('graphPanel.actions.hideTitle', 'Masquer la sélection')}</DialogTitle>
            <DialogDescription>
              {t('graphPanel.actions.hideDescription',
                `Vous allez masquer ${selectedNodes.size} nœud(s) et ${selectedEdges.size} relation(s) de la visualisation. Les éléments ne seront pas supprimés du graphe - rechargez la page pour les restaurer.`
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="flex gap-2 justify-end">
            <Button variant="ghost" onClick={() => setShowDeleteDialog(false)}>
              {t('common.cancel', 'Annuler')}
            </Button>
            <Button variant="secondary" onClick={handleDeleteSelection}>
              {t('common.confirm', 'Confirmer')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={showPermanentDeleteDialog} onOpenChange={setShowPermanentDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('graphPanel.actions.deleteTitle', 'Supprimer définitivement l\'entité')}</DialogTitle>
            <DialogDescription>
              {t('graphPanel.actions.deleteDescription',
                'Vous allez supprimer définitivement cette entité et toutes ses relations du graphe de connaissances. Cette action est irréversible.'
              )}
            </DialogDescription>
          </DialogHeader>
          <div className="bg-red-50 dark:bg-red-950/30 border border-red-200 dark:border-red-800 p-3 rounded text-sm text-red-700 dark:text-red-300 mb-4">
            <AlertCircleIcon className="w-4 h-4 inline mr-2" />
            {t('graphPanel.actions.deleteWarning', 'Action irréversible - les données seront supprimées définitivement')}
          </div>
          <div className="flex gap-2 justify-end">
            <Button 
              variant="ghost" 
              onClick={() => setShowPermanentDeleteDialog(false)}
              disabled={isDeleting}
            >
              {t('common.cancel', 'Annuler')}
            </Button>
            <Button 
              variant="destructive" 
              onClick={handlePermanentDelete}
              disabled={isDeleting}
            >
              {isDeleting ? t('common.loading', 'Suppression...') : t('common.delete', 'Supprimer')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </>
  )
}
